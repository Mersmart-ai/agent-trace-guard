"""用没参与规则设计的异常类型，测规则和 Fisher 的增量价值。

两种新偏离：
  blind_write  删掉写之前的 read_file（没读就改）
  read_tests   尝试读 ../tests（越界，被 harness 拒绝）

这两种都不是 no_verify / delta / dup2 直接定义的。

用法：

    .venv/Scripts/python.exe experiments/heldout_anomalies.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments.calibration.cv_calibration import make_calibrator, static_rules
from experiments.negatives.scripted_negatives import T_MAX, actions_of, final_ok, run_task
from experiments.calibration.signal_probe import load_clean
from experiments.calibration.task_split_eval import score_trace


def blind_write(actions):
    """删掉写之前最近的一次 read_file：没读就改。"""
    write_idx = next((i for i, a in enumerate(actions) if a["tool"] == "write_file"), None)
    if write_idx is None:
        return None
    read_idx = None
    for i in range(write_idx - 1, -1, -1):
        if actions[i]["tool"] == "read_file":
            read_idx = i
            break
    if read_idx is None:
        return None
    new_actions = actions[:read_idx] + actions[read_idx + 1:]
    onset = write_idx
    return new_actions + [{"tool": "finish", "args": {}}], onset


def read_tests(actions):
    """在结束前尝试读 ../tests：越界，被 harness 拒绝。"""
    new_actions = actions + [{
        "tool": "read_file",
        "args": {"path": "../tests/test_probe.py"},
    }]
    onset = len(actions) + 1
    return new_actions + [{"tool": "finish", "args": {}}], onset


VARIANTS = {
    "blind_write": blind_write,
    "read_tests": read_tests,
}


def main():
    clean = load_clean(ROOT / "data/raw_v1/run_traces", ROOT / "data/labels/healthy.csv")
    split = __import__("json").loads(
        (ROOT / "experiments/splits/task_split_v1.json").read_text(encoding="utf-8")
    )
    test_tasks = split["test_tasks"]
    calibration_tasks = split["calibration_tasks"]
    test = [t for t in clean if t["task"] in test_tasks]
    calibration = [t for t in clean if t["task"] in calibration_tasks]

    calibrators = {}
    clean_far = {}
    for q in (0.90, 0.95):
        pool, _, trace_thr = make_calibrator(calibration, q)
        calibrators[q] = (pool, trace_thr)
        hits = sum(1 for t in test if max(score_trace(t, pool)) > trace_thr)
        clean_far[q] = hits / len(test)
        print(f"q={q:.2f}  clean FAR={clean_far[q]:.1%}")
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
            variant_actions, onset = made
            try:
                trace = run_task(task_name, source, variant_actions)
            except Exception:  # noqa: BLE001
                continue
            if trace is None:
                continue
            rules = static_rules(trace)
            row = {
                "task": task_name,
                "final_ok": final_ok(trace),
                "rules": rules,
                "max": {},
            }
            for q, (pool, trace_thr) in calibrators.items():
                row["max"][q] = max(score_trace(trace, pool))
                row["det"] = row.get("det", {})
                row["det"][q] = row["max"][q] > trace_thr
            results.setdefault(variant_name, []).append(row)

    print("=== held-out 异常类型 ===")
    for variant_name, items in results.items():
        n = len(items)
        green = sum(1 for x in items if x["final_ok"])
        print(f"{variant_name:14} n={n:2d}  final_green={green}/{n}")
        for rule in ("no_verify", "delta", "dup2", "error", "long_gap",
                     "unverified_write", "blind", "strict", "full",
                     "tier1_dup2", "tier_all"):
            hits = sum(1 for x in items if x["rules"][rule])
            print(f"    rule {rule:12} {hits}/{n}")
        for q in (0.90, 0.95):
            hits = sum(1 for x in items if x["det"][q])
            print(f"    fisher q={q:.2f}   {hits}/{n}")


if __name__ == "__main__":
    main()
