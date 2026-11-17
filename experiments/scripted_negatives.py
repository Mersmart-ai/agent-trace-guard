"""用脚本重放 clean trace，并注入 harness 允许的偏离，生成真实执行的负样本。

和 signal_probe 的区别：
  - signal_probe 是事后改 JSON，特征是我们直接改出来的
  - 这里是真的跑一遍工具和测试，test_state 是 harness 真实判出来的

不调用模型、不花 API。
用法（任意目录）：

    .venv/Scripts/python.exe experiments/scripted_negatives.py

只做 4 种 harness 允许的偏离：
  skip_verify   不主动 run_tests 就 finish
  loop_read     重复读同一个文件
  repeat_write  重复写同一个内容
  regression    写坏、测试变红、再修好
"""
import argparse
import copy
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fbs.agent.loop import agent_loop
from fbs.data.trace import prepare_workspace
from fbs.legacy.locate import build_states, locate

from experiments.signal_probe import (
    FEATURES, build_pool, build_rows, clean_scores_by_trace,
    fisher, load_clean, percentile,
)

DEFAULT_TASKS = ["task_0001", "task_0003", "task_0006", "task_0009", "task_0014"]
T_MAX = 8


def actions_of(trace):
    """把 clean trace 变成可重放的 action 列表；去掉 finish，最后统一补一个。"""
    actions = []
    for step in trace["steps"]:
        if step.get("tool") == "finish":
            continue
        actions.append({
            "tool": step.get("tool"),
            "args": step.get("args") or {},
        })
    return actions


def with_finish(actions):
    return actions + [{"tool": "finish", "args": {}}]


def variant_skip_verify(actions):
    """删掉最后一次 run_tests：模拟没主动验证就交差。"""
    idx = max((i for i, a in enumerate(actions) if a["tool"] == "run_tests"), default=None)
    if idx is None:
        return None
    new_actions = actions[:idx] + actions[idx + 1:]
    return with_finish(new_actions), idx + 1


def variant_loop_read(actions):
    """把第一次读操作重复 4 次：模拟打转。"""
    idx = next((i for i, a in enumerate(actions) if a["tool"] in ("read_file", "list_files")), None)
    if idx is None:
        return None
    copies = [copy.deepcopy(actions[idx]) for _ in range(4)]
    new_actions = actions[:idx + 1] + copies + actions[idx + 1:]
    return with_finish(new_actions), idx + 2


def variant_repeat_write(actions):
    """把第一次写重复 3 次：模拟反复改同一处。"""
    idx = next((i for i, a in enumerate(actions) if a["tool"] == "write_file"), None)
    if idx is None:
        return None
    copies = [copy.deepcopy(actions[idx]) for _ in range(3)]
    new_actions = actions[:idx + 1] + copies + actions[idx + 1:]
    return with_finish(new_actions), idx + 2


def variant_regression(actions):
    """写坏、测试变红、再修好：模拟 absorbed error。"""
    test_idx = next((i for i, a in enumerate(actions) if a["tool"] == "run_tests"), None)
    if test_idx is None:
        return None
    write_idx = next((i for i in range(test_idx) if actions[i]["tool"] == "write_file"), None)
    if write_idx is None:
        return None

    path = actions[write_idx]["args"]["path"]
    good = actions[write_idx]["args"]["content"]
    bad = good.rstrip() + "\n\nraise RuntimeError('probe_regression')\n"
    inject = [
        {"tool": "write_file", "args": {"path": path, "content": bad}},
        {"tool": "run_tests", "args": {}},
        {"tool": "write_file", "args": {"path": path, "content": good}},
        {"tool": "run_tests", "args": {}},
    ]
    new_actions = actions[:test_idx + 1] + inject + actions[test_idx + 1:]
    return with_finish(new_actions), test_idx + 2


VARIANTS = {
    "skip_verify": variant_skip_verify,
    "loop_read": variant_loop_read,
    "repeat_write": variant_repeat_write,
    "regression": variant_regression,
}


def replay_policy(actions):
    """按顺序返回 action；用完了就 finish。"""
    def policy(step, history):
        index = step - 1
        if index < len(actions):
            return actions[index]
        return {"tool": "finish", "args": {}}
    return policy


def run_task(task_name, source_trace, actions):
    """在临时工作区重放一组 action，返回真实执行出来的 trace dict。"""
    task_dir = ROOT / "tasks" / task_name
    meta_file = task_dir / "meta.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}
    if meta.get("rounds"):
        return None

    opts = {}
    for key in ("python", "visible_command", "judge_command"):
        if meta.get(key):
            opts[key] = meta[key]

    hidden = task_dir / "tests_hidden"
    judge_tests = hidden if hidden.is_dir() else None
    if opts.get("judge_command"):
        judge_tests = None

    with tempfile.TemporaryDirectory() as tmp:
        workspace = prepare_workspace(task_dir, Path(tmp))
        if workspace is None:
            return None
        history, reason = agent_loop(
            workspace,
            task_dir / "tests",
            replay_policy(actions),
            judge_tests=judge_tests,
            opts=opts,
        )

    return {
        "run_id": f"{source_trace['run_id']}_scripted",
        "task": task_name,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "reason": reason,
        "steps": history,
        "source_run_id": source_trace["run_id"],
    }


def final_ok(trace):
    return locate(build_states(trace["steps"])) == {}


def deviation_happened(variant, trace):
    """确认扰动真的发生了，而不是脚本没生效。"""
    rows = build_rows([trace], T_MAX)[0]
    if variant == "regression":
        return any(r["vec"]["delta_fails"] > 0 for r in rows)
    if variant in ("loop_read", "repeat_write"):
        return any(r["vec"]["is_dup"] > 0 for r in rows)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", nargs="*", default=DEFAULT_TASKS)
    args = ap.parse_args()

    clean = load_clean(ROOT / "data/raw_v1/run_traces", ROOT / "data/labels/healthy.csv")
    by_id = {t["run_id"]: t for t in clean}
    clean_rows = build_rows(clean, T_MAX)
    pool = build_pool(clean_rows)
    by_trace = clean_scores_by_trace(clean_rows, pool)
    all_steps = [s for row in by_trace for s in row]
    step_thr = percentile(all_steps, 0.9)
    trace_thr = percentile([max(row) for row in by_trace], 0.9)
    index_of = {t["run_id"]: i for i, t in enumerate(clean)}

    print(f"clean={len(clean)}  step_thr={step_thr:.2f}  trace_thr={trace_thr:.2f}")
    print()

    results = {}
    for task_name in args.tasks:
        sources = [t for t in clean if t["task"] == task_name]
        if not sources:
            print(f"{task_name}: 没有 clean trace，跳过")
            continue
        source = sources[0]
        actions = actions_of(source)

        for variant_name, fn in VARIANTS.items():
            made = fn(actions)
            if made is None:
                continue
            variant_actions, onset = made
            trace = run_task(task_name, source, variant_actions)
            if trace is None:
                continue
            trace["variant"] = variant_name
            trace["onset"] = onset
            if not deviation_happened(variant_name, trace):
                print(f"{task_name:12} {variant_name:14} 扰动没生效，跳过")
                continue

            rows = build_rows([trace], T_MAX)[0]
            source_index = index_of[source["run_id"]]
            scores = [
                fisher(item["vec"], item["kind"], pool, exclude=source_index)
                for item in rows
            ]
            max_score = max(scores) if scores else 0.0
            step_alarm = next(
                (t for t in range(onset, len(scores) + 1) if scores[t - 1] > step_thr),
                None,
            )
            trace_alarm = max_score > trace_thr
            results.setdefault(variant_name, []).append({
                "task": task_name,
                "final_ok": final_ok(trace),
                "max_score": max_score,
                "trace_alarm": trace_alarm,
                "step_alarm": step_alarm,
                "onset": onset,
            })
            print(
                f"{task_name:12} {variant_name:14} "
                f"max={max_score:5.2f}  "
                f"trace={'报警' if trace_alarm else '没报'}  "
                f"step={'报警' if step_alarm else '没报'}  "
                f"final={'绿' if final_ok(trace) else '红'}"
            )

    print()
    print("=== 汇总 ===")
    for variant_name, items in results.items():
        n = len(items)
        trace_hits = sum(1 for x in items if x["trace_alarm"])
        step_hits = sum(1 for x in items if x["step_alarm"] is not None)
        finals = sum(1 for x in items if x["final_ok"])
        delays = sorted(
            x["step_alarm"] - x["onset"] for x in items
            if x["step_alarm"] is not None
        )
        median_delay = delays[len(delays) // 2] if delays else None
        print(
            f"{variant_name:14} n={n}  "
            f"trace={trace_hits}/{n}  "
            f"step={step_hits}/{n}  "
            f"final_green={finals}/{n}  "
            f"median_delay={median_delay}"
        )


if __name__ == "__main__":
    main()
