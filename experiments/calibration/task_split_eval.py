"""任务级切分：在没参与校准的任务上，重算误报和检出。

和 scripted_negatives 的区别：
  - 之前：阈值用全部 clean 定，测试任务也在里面（偏乐观）
  - 现在：一部分任务只用于校准，另一部分任务完全留出

不调用模型、不花 API。
用法：

    .venv/Scripts/python.exe experiments/task_split_eval.py
"""
import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments.negatives.scripted_negatives import (
    T_MAX, VARIANTS, actions_of, deviation_happened, final_ok, run_task,
)
from experiments.calibration.signal_probe import (
    build_pool, build_rows, clean_scores_by_trace, fisher, load_clean, percentile,
)

DEFAULT_SEED = 20261115
DEFAULT_TEST_SIZE = 15


def split_tasks(clean_traces, test_size, seed):
    """按任务切分；同一任务的 trace 不会跨两边。"""
    tasks = sorted({t["task"] for t in clean_traces})
    rng = random.Random(seed)
    rng.shuffle(tasks)
    test_tasks = sorted(tasks[:test_size])
    calibration_tasks = sorted(tasks[test_size:])
    return calibration_tasks, test_tasks


def score_trace(trace, pool):
    rows = build_rows([trace], T_MAX)[0]
    return [fisher(item["vec"], item["kind"], pool) for item in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--test-size", type=int, default=DEFAULT_TEST_SIZE)
    args = ap.parse_args()

    clean = load_clean(ROOT / "data/raw_v1/run_traces", ROOT / "data/labels/healthy.csv")
    calibration_tasks, test_tasks = split_tasks(clean, args.test_size, args.seed)

    split_path = ROOT / "experiments/splits/task_split_v1.json"
    split_path.parent.mkdir(parents=True, exist_ok=True)
    split_path.write_text(json.dumps({
        "seed": args.seed,
        "test_size": args.test_size,
        "calibration_tasks": calibration_tasks,
        "test_tasks": test_tasks,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    calibration = [t for t in clean if t["task"] in calibration_tasks]
    test = [t for t in clean if t["task"] in test_tasks]

    calibration_rows = build_rows(calibration, T_MAX)
    pool = build_pool(calibration_rows)
    calibration_scores = clean_scores_by_trace(calibration_rows, pool)
    all_calibration_steps = [s for row in calibration_scores for s in row]
    step_thr = percentile(all_calibration_steps, 0.9)
    trace_thr = percentile([max(row) for row in calibration_scores], 0.9)

    print(f"calibration tasks={len(calibration_tasks)} traces={len(calibration)}")
    print(f"test tasks={len(test_tasks)} traces={len(test)}")
    print(f"pool sizes: { {k: len(v) for k, v in sorted(pool.items())} }")
    print(f"step_thr={step_thr:.2f}  trace_thr={trace_thr:.2f}")
    print()

    # 留出任务上的 clean 误报
    test_scores = [score_trace(t, pool) for t in test]
    test_trace_hits = sum(1 for s in test_scores if max(s) > trace_thr)
    test_steps = [x for s in test_scores for x in s]
    test_step_hits = sum(1 for x in test_steps if x > step_thr)
    print(f"留出 clean 轨迹误报：{test_trace_hits}/{len(test)} = {test_trace_hits / len(test):.1%}")
    print(f"留出 clean 步级误报：{test_step_hits}/{len(test_steps)} = {test_step_hits / len(test_steps):.1%}")
    for trace, scores in zip(test, test_scores):
        if max(scores) > trace_thr:
            print(f"  误报: {trace['run_id']} max={max(scores):.2f}")
    print()

    # 只在留出任务上生成脚本负样本
    results = {}
    test_by_id = {t["run_id"]: t for t in test}
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
            except Exception as exc:  # noqa: BLE001 - 单个任务失败不拖垮整批
                print(f"  {task_name} {variant_name}: 运行失败 {exc}")
                continue
            if trace is None:
                continue
            if not deviation_happened(variant_name, trace):
                continue

            scores = score_trace(trace, pool)
            max_score = max(scores) if scores else 0.0
            step_alarm = next(
                (t for t in range(onset, len(scores) + 1) if scores[t - 1] > step_thr),
                None,
            )
            if max_score <= trace_thr:
                print(f"  漏检: {task_name} {variant_name} max={max_score:.2f} onset={onset}")
            results.setdefault(variant_name, []).append({
                "task": task_name,
                "final_ok": final_ok(trace),
                "trace_alarm": max_score > trace_thr,
                "step_alarm": step_alarm,
                "onset": onset,
                "max_score": max_score,
            })

    print("=== 留出任务上的脚本负样本 ===")
    for variant_name, items in results.items():
        n = len(items)
        trace_hits = sum(1 for x in items if x["trace_alarm"])
        step_hits = sum(1 for x in items if x["step_alarm"] is not None)
        green = sum(1 for x in items if x["final_ok"])
        delays = sorted(
            x["step_alarm"] - x["onset"] for x in items if x["step_alarm"] is not None
        )
        median_delay = delays[len(delays) // 2] if delays else None
        print(
            f"{variant_name:14} n={n:2d}  trace={trace_hits}/{n}  "
            f"step={step_hits}/{n}  final_green={green}/{n}  "
            f"median_delay={median_delay}"
        )


if __name__ == "__main__":
    main()
