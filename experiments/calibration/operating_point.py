"""固定任务切分，扫多个阈值分位，看误报和检出的权衡。

不重新训练、不调模型，只回答：
  把阈值从 90 分位提高到 95/97.5/99 分位，
  误报能降多少，检出会掉多少。

用法：

    .venv/Scripts/python.exe experiments/operating_point.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from experiments.negatives.scripted_negatives import (
    T_MAX, VARIANTS, actions_of, deviation_happened, final_ok, run_task,
)
from experiments.calibration.signal_probe import (
    FEATURES, MIN_POOL, build_pool, build_rows, clean_scores_by_trace,
    emp_p, fisher, load_clean, percentile,
)
from experiments.calibration.task_split_eval import DEFAULT_SEED, split_tasks, score_trace

QUANTILES = [0.90, 0.95, 0.975, 0.99]


def top_features(step_vec, kind, pool, n=3):
    """这一步贡献最大的几个特征。"""
    items = []
    for f in FEATURES:
        vals = [v[f] for _, v in pool.get(kind, [])]
        if len(vals) < MIN_POOL:
            continue
        p = emp_p(step_vec[f], vals)
        items.append((p, f, step_vec[f]))
    items.sort()
    return items[:n]


def main():
    clean = load_clean(ROOT / "data/raw_v1/run_traces", ROOT / "data/labels/healthy.csv")
    calibration_tasks, test_tasks = split_tasks(clean, 15, DEFAULT_SEED)
    calibration = [t for t in clean if t["task"] in calibration_tasks]
    test = [t for t in clean if t["task"] in test_tasks]

    calibration_rows = build_rows(calibration, T_MAX)
    pool = build_pool(calibration_rows)
    calibration_scores = clean_scores_by_trace(calibration_rows, pool)
    all_steps = [s for row in calibration_scores for s in row]
    calibration_max = [max(row) for row in calibration_scores]

    test_scores = [score_trace(t, pool) for t in test]

    scripted = []
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
            if trace is None or not deviation_happened(variant_name, trace):
                continue
            scripted.append({
                "variant": variant_name,
                "scores": score_trace(trace, pool),
                "onset": onset,
                "final_ok": final_ok(trace),
            })

    print(f"calibration traces={len(calibration)}  test traces={len(test)}  scripted={len(scripted)}")
    print()

    for q in QUANTILES:
        step_thr = percentile(all_steps, q)
        trace_thr = percentile(calibration_max, q)

        far = sum(1 for s in test_scores if max(s) > trace_thr) / len(test_scores)
        step_far = sum(
            1 for s in test_scores for x in s if x > step_thr
        ) / sum(len(s) for s in test_scores)

        print(f"=== q={q:.3f}  step_thr={step_thr:.2f}  trace_thr={trace_thr:.2f} ===")
        print(f"clean 轨迹误报：{far:.1%}   clean 步级误报：{step_far:.1%}")

        for variant_name in VARIANTS:
            items = [s for s in scripted if s["variant"] == variant_name]
            if not items:
                continue
            hits = sum(1 for s in items if max(s["scores"]) > trace_thr)
            step_hits = sum(
                1 for s in items
                if any(x > step_thr for x in s["scores"][s["onset"] - 1:])
            )
            print(f"  {variant_name:14} trace={hits}/{len(items)}  step={step_hits}/{len(items)}")
        print()

    # 90 分位下的误报，看看是哪些特征把它们顶上去的
    trace_thr = percentile(calibration_max, 0.90)
    print("=== q=0.90 的误报原因 ===")
    for trace, scores in zip(test, test_scores):
        if max(scores) <= trace_thr:
            continue
        rows = build_rows([trace], T_MAX)[0]
        best_t = max(range(len(scores)), key=lambda i: scores[i])
        item = rows[best_t]
        print(f"{trace['run_id']}  max={scores[best_t]:.2f}  step={best_t + 1}")
        for p, f, x in top_features(item["vec"], item["kind"], pool):
            print(f"    {f:14} x={x:5.1f}  p={p:.3f}")


if __name__ == "__main__":
    main()
