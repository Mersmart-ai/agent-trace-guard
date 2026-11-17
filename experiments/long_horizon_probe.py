"""长程故障注入：把已知偏离放进真实的长程 trace，看规则还能不能抓到。

0 API；全部通过 run_task 真实执行。
长程定义：>=10 步的单轮 trace。

用法：

    .venv/Scripts/python.exe experiments/long_horizon_probe.py
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fbs.analysis.features import step_features
from fbs.analysis.monitor import STRICT_RULES, rule_alarms
from experiments.cv_calibration import make_calibrator
from experiments.scripted_negatives import (
    T_MAX, VARIANTS as BASE_VARIANTS, actions_of, final_ok, run_task,
)
from experiments.signal_probe import build_rows, fisher, load_clean
from experiments.task_split_eval import score_trace

MIN_STEPS = 10
FINISH = {"tool": "finish", "args": {}}


def skip_final_verify(actions):
    """删掉最后一次写之后的所有 run_tests：最终改动没有验证。"""
    writes = [i for i, a in enumerate(actions) if a["tool"] == "write_file"]
    if not writes:
        return None
    last_write = writes[-1]
    tests = [i for i in range(last_write + 1, len(actions)) if actions[i]["tool"] == "run_tests"]
    if not tests:
        return None
    kept = [
        a for i, a in enumerate(actions)
        if not (i > last_write and a["tool"] == "run_tests")
    ]
    return kept + [FINISH], last_write + 2


VARIANTS = dict(BASE_VARIANTS)
VARIANTS["skip_final_verify"] = skip_final_verify


def load_labels():
    path = ROOT / "data" / "labels" / "healthy.csv"
    return {
        r["run_id"]: r["healthy_class"]
        for r in csv.DictReader(path.open(encoding="utf-8"))
    }


def load_sources():
    labels = load_labels()
    sources = []

    for path in sorted((ROOT / "data" / "raw_v1" / "run_traces").rglob("*.json")):
        trace = json.loads(path.read_text(encoding="utf-8"))
        if labels.get(trace["run_id"]) != "clean_success":
            continue
        if len(trace["steps"]) < MIN_STEPS:
            continue
        sources.append(trace)

    for path in sorted((ROOT / "data" / "traces" / "real").rglob("*.json")):
        trace = json.loads(path.read_text(encoding="utf-8"))
        if len(trace["steps"]) < MIN_STEPS:
            continue
        sources.append(trace)

    return sources


def task_has_rounds(task_name):
    meta_file = ROOT / "tasks" / task_name / "meta.json"
    if not meta_file.exists():
        return False
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    return bool(meta.get("rounds"))


def deviation_ok(name, trace, onset):
    rows = step_features(trace)
    post = rows[onset - 1:]
    if name in ("skip_verify", "skip_final_verify"):
        return True
    if name == "regression":
        return any(r["delta_fails"] > 0 for r in post)
    if name in ("loop_read", "repeat_write"):
        return any(r["is_dup"] for r in post)
    return False


def main():
    clean = load_clean(ROOT / "data/raw_v1/run_traces", ROOT / "data/labels/healthy.csv")
    split = json.loads(
        (ROOT / "experiments/splits/task_split_v1.json").read_text(encoding="utf-8")
    )
    calibration = [
        t for t in clean if t["task"] in set(split["calibration_tasks"])
    ]
    pool, _, trace_thr = make_calibrator(calibration, 0.95)
    test = [t for t in clean if t["task"] in split["test_tasks"]]
    clean_far = sum(
        1 for t in test if max(score_trace(t, pool)) > trace_thr
    ) / len(test)
    print(f"clean Fisher FAR q=0.95: {clean_far:.1%}")
    print(f"trace_thr={trace_thr:.2f}")

    sources = [t for t in load_sources() if not task_has_rounds(t["task"])]
    print(f"long sources: {len(sources)}")
    print()

    results = {}
    for source in sources:
        task = source["task"]
        actions = actions_of(source)
        for name, fn in VARIANTS.items():
            made = fn(actions)
            if made is None:
                continue
            new_actions, onset = made
            try:
                trace = run_task(task, source, new_actions)
            except Exception:  # noqa: BLE001
                continue
            if trace is None or not final_ok(trace):
                continue
            if not deviation_ok(name, trace, onset):
                continue

            alarms = rule_alarms(trace["steps"])
            post_alarms = [a for a in alarms if a["step"] >= onset]
            strict_hits = [a for a in post_alarms if a["rule"] in STRICT_RULES]
            full_hits = post_alarms

            # Fisher 用完整长程 trace 打分；但校准池只有前 8 步的 kind 参考，
            # 所以这里只作对照，主结论看规则。
            rows = build_rows([trace], len(trace["steps"]))[0]
            scores = [
                fisher(item["vec"], item["kind"], pool) for item in rows
            ]
            fisher_hit = max(scores[onset - 1:]) > trace_thr
            delay = (
                strict_hits[0]["step"] - onset if strict_hits else None
            )

            results.setdefault(name, []).append({
                "source": source["run_id"],
                "task": task,
                "steps": len(trace["steps"]),
                "onset": onset,
                "strict": [a["rule"] for a in strict_hits],
                "full": [a["rule"] for a in full_hits],
                "fisher": fisher_hit,
                "delay": delay,
            })

    print("=== 长程注入结果 ===")
    for name, items in results.items():
        n = len(items)
        if not n:
            continue
        strict_hits = sum(1 for x in items if x["strict"])
        full_hits = sum(1 for x in items if x["full"])
        fisher_hits = sum(1 for x in items if x["fisher"])
        delays = sorted(x["delay"] for x in items if x["delay"] is not None)
        median_delay = delays[len(delays) // 2] if delays else None
        print(
            f"{name:14} n={n:2d}  strict={strict_hits}/{n}  full={full_hits}/{n}  "
            f"fisher95={fisher_hits}/{n}  median_delay={median_delay}"
        )
        for x in items:
            print(
                f"    {x['source']:32} steps={x['steps']:2d} onset={x['onset']:2d} "
                f"strict={x['strict']} full={x['full']} fisher={x['fisher']}"
            )


if __name__ == "__main__":
    main()
