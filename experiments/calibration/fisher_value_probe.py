"""Fisher 增量价值探针：规则漏检的多特征偏离，Fisher 能不能抓到。

严格标准（用户确认）：
  - 规则检出 <= 20%（严格规则和完整规则都要看）
  - Fisher q=0.95 检出 >= 60%
  - 留出 clean 的 Fisher FAR <= 15%

0 API；全部通过 run_task 真实执行。

用法：

    .venv/Scripts/python.exe experiments/fisher_value_probe.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments.calibration.cv_calibration import make_calibrator, static_rules
from experiments.negatives.scripted_negatives import T_MAX, actions_of, final_ok, run_task
from experiments.calibration.signal_probe import load_clean
from experiments.calibration.task_split_eval import score_trace

FINISH = {"tool": "finish", "args": {}}
GREP_PATTERNS = ["def", "return", "import", "class", "if", "for", "while"]


def grep_steps(n):
    """n 个不同的 grep 动作，避免被 dup2 当成连续重复。"""
    return [
        {"tool": "grep", "args": {"pattern": GREP_PATTERNS[i % len(GREP_PATTERNS)]}}
        for i in range(n)
    ]


def long_gap(actions):
    """在 write 和 test 之间插入不同文件的 grep：since_test 拉高，但没重复。"""
    write_idx = next((i for i, a in enumerate(actions) if a["tool"] == "write_file"), None)
    if write_idx is None:
        return None
    test_idx = next(
        (i for i in range(write_idx + 1, len(actions)) if actions[i]["tool"] == "run_tests"),
        None,
    )
    if test_idx is None:
        return None
    # 插入后 test 会被推到 1-based 的 test_idx+4；超出 T_MAX 就没有校准参考
    if test_idx + 4 > T_MAX:
        return None
    new_actions = actions[:test_idx] + grep_steps(3) + actions[test_idx:]
    return new_actions + [FINISH], test_idx + 1


def late_nav(actions):
    """最后一次 test 之后、finish 之前插入 grep：since_test 拉高。"""
    test_idx = max(
        (i for i, a in enumerate(actions) if a["tool"] == "run_tests"),
        default=None,
    )
    if test_idx is None:
        return None
    # 插入后 finish 在 1-based 的 test_idx+5；超出 T_MAX 就看不到异常步
    if test_idx + 5 > T_MAX:
        return None
    new_actions = actions[:test_idx + 1] + grep_steps(3) + actions[test_idx + 1:]
    return new_actions + [FINISH], test_idx + 2


def many_cycles(actions):
    """插入多轮 write→test，内容不同：n_verify 拉高，但没有连续重复。"""
    write_idx = next((i for i, a in enumerate(actions) if a["tool"] == "write_file"), None)
    if write_idx is None:
        return None
    test_idx = next(
        (i for i in range(write_idx + 1, len(actions)) if actions[i]["tool"] == "run_tests"),
        None,
    )
    if test_idx is None:
        return None

    if test_idx + 5 > T_MAX:
        return None
    path = actions[write_idx]["args"]["path"]
    content = actions[write_idx]["args"]["content"]
    cycles = []
    for k in range(2):
        cycles.append({
            "tool": "write_file",
            "args": {"path": path, "content": content + f"\n# probe_cycle_{k}\n"},
        })
        cycles.append({"tool": "run_tests", "args": {}})

    new_actions = actions[:test_idx + 1] + cycles + actions[test_idx + 1:]
    return new_actions + [FINISH], test_idx + 2


def per_file_blind(actions):
    """读 A，写 B 但没读 B；第一次写之前仍有其他 read_file，所以 blind 规则会漏。"""
    write_idx = next((i for i, a in enumerate(actions) if a["tool"] == "write_file"), None)
    if write_idx is None:
        return None

    path = actions[write_idx]["args"]["path"]
    reads_same = [
        i for i in range(write_idx)
        if actions[i]["tool"] == "read_file" and actions[i]["args"].get("path") == path
    ]
    reads_other = [
        i for i in range(write_idx)
        if actions[i]["tool"] == "read_file" and actions[i]["args"].get("path") != path
    ]
    if not reads_same or not reads_other:
        return None
    if write_idx > T_MAX:
        return None

    remove_at = reads_same[-1]
    new_actions = actions[:remove_at] + actions[remove_at + 1:]
    # 删掉一步后，原来的 write 下标变成 write_idx-1（0-based），1-based 仍是 write_idx
    return new_actions + [FINISH], write_idx


VARIANTS = {
    "long_gap": long_gap,
    "late_nav": late_nav,
    "many_cycles": many_cycles,
    "per_file_blind": per_file_blind,
}


def deviation_ok(variant, trace, source):
    if not final_ok(trace):
        return False
    src_tools = [h.get("tool") for h in source["steps"]]
    new_tools = [h.get("tool") for h in trace["steps"]]
    if variant in ("long_gap", "late_nav"):
        return len(new_tools) >= len(src_tools) + 3
    if variant == "many_cycles":
        return new_tools.count("run_tests") > src_tools.count("run_tests")
    if variant == "per_file_blind":
        return True
    return False


def main():
    clean = load_clean(ROOT / "data/raw_v1/run_traces", ROOT / "data/labels/healthy.csv")
    split = json.loads(
        (ROOT / "experiments/splits/task_split_v1.json").read_text(encoding="utf-8")
    )
    calibration_tasks = set(split["calibration_tasks"])
    test_tasks = split["test_tasks"]

    calibration = [t for t in clean if t["task"] in calibration_tasks]
    test = [t for t in clean if t["task"] in test_tasks]

    calibrators = {}
    clean_far = {}
    print("=== clean FAR ===")
    for q in (0.90, 0.95):
        pool, _, trace_thr = make_calibrator(calibration, q)
        calibrators[q] = (pool, trace_thr)
        fisher_hits = sum(1 for t in test if max(score_trace(t, pool)) > trace_thr)
        clean_far[q] = fisher_hits / len(test)
        strict_hits = 0
        full_hits = 0
        for t in test:
            rules = static_rules(t)
            if rules["strict"]:
                strict_hits += 1
            if rules["full"]:
                full_hits += 1
        print(
            f"q={q:.2f}  fisher={fisher_hits}/{len(test)}={clean_far[q]:.1%}  "
            f"strict_rules={strict_hits/len(test):.1%}  full_rules={full_hits/len(test):.1%}"
        )
    print()

    results = {}
    for task_name in test_tasks:
        sources = [t for t in test if t["task"] == task_name]
        if not sources:
            continue
        source = sources[0]
        actions = actions_of(source)

        for variant_name, fn in VARIANTS.items():
            made = fn(actions)
            if made is None:
                continue
            new_actions, onset = made
            try:
                trace = run_task(task_name, source, new_actions)
            except Exception:  # noqa: BLE001 - 单个任务失败不拖垮整批
                continue
            if trace is None or not deviation_ok(variant_name, trace, source):
                continue

            rules = static_rules(trace)
            rule_strict = rules["strict"]
            rule_full = rules["full"]

            pool95, thr95 = calibrators[0.95]
            prealarmed = max(score_trace(source, pool95)) > thr95
            row = {
                "task": task_name,
                "strict": rule_strict,
                "full": rule_full,
                "fisher": {},
                "final_ok": final_ok(trace),
                "prealarmed": prealarmed,
            }
            for q, (pool, trace_thr) in calibrators.items():
                row["fisher"][q] = max(score_trace(trace, pool)) > trace_thr
            results.setdefault(variant_name, []).append(row)

    print("=== 规则漏检的变体 ===")
    passed_any = False
    for variant_name, items in results.items():
        n = len(items)
        if not n:
            continue
        strict_hits = sum(1 for x in items if x["strict"])
        full_hits = sum(1 for x in items if x["full"])
        fisher90 = sum(1 for x in items if x["fisher"][0.90])
        fisher95 = sum(1 for x in items if x["fisher"][0.95])
        green = sum(1 for x in items if x["final_ok"])
        nonpre = [x for x in items if not x["prealarmed"]]
        fisher95_nonpre = sum(1 for x in nonpre if x["fisher"][0.95])
        print(
            f"{variant_name:14} n={n:2d}  final_green={green}/{n}  "
            f"strict={strict_hits}/{n}  full={full_hits}/{n}  "
            f"fisher90={fisher90}/{n}  fisher95={fisher95}/{n}  "
            f"nonpre={len(nonpre)}  fisher95_nonpre={fisher95_nonpre}/{len(nonpre)}"
        )
        rule_rates_ok = (
            strict_hits / n <= 0.20 and full_hits / n <= 0.20
        )
        fisher95_ok = bool(nonpre) and fisher95_nonpre / len(nonpre) >= 0.60
        far_ok = clean_far[0.95] <= 0.15
        print(
            f"    strict/full<=20%: {rule_rates_ok}  "
            f"fisher95>=60%: {fisher95_ok}  "
            f"fisher_far95={clean_far[0.95]:.1%}<=15%: {far_ok}"
        )
        if rule_rates_ok and fisher95_ok and far_ok:
            passed_any = True

    print()
    print("=== 判定 ===")
    print("通过严格标准：", "有" if passed_any else "没有")
    print("注：通过还需 clean Fisher FAR q=0.95 <=15%，见上方 clean FAR 行。")


if __name__ == "__main__":
    main()
