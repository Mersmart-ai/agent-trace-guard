"""固定测试任务集，做 5 折校准，比较 Fisher 和简单规则。

回答两个问题：
  1. 换一批校准任务，误报和检出稳不稳
  2. 复杂模型有没有比简单规则更好

不调用模型、不花 API。
用法：

    .venv/Scripts/python.exe experiments/cv_calibration.py
"""
import json
import random
import statistics
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
from experiments.calibration.task_split_eval import score_trace
from fbs.analysis.features import step_features
from fbs.analysis.monitor import STRICT_RULES, rule_alarms

QS = [0.90, 0.95]
N_FOLDS = 5


def make_calibrator(cal_traces, q):
    rows = build_rows(cal_traces, T_MAX)
    pool = build_pool(rows)
    scores = clean_scores_by_trace(rows, pool)
    step_thr = percentile([s for row in scores for s in row], q)
    trace_thr = percentile([max(row) for row in scores], q)
    return pool, step_thr, trace_thr


def static_rules(trace):
    """实验版规则基线：直接复用正式 monitor，避免两套规则分叉。

    仍然只看前 T_MAX 步，保持和历史实验的窗口一致。
    `dup` 不是正式规则，保留给旧的 cv 输出。

    注意：窗口截断后，末尾的 unverified_write 可能只是“后面还有测试没看到”；
    完整 trace 的监控请直接用 monitor.rule_alarms。
    """
    steps = (trace.get("steps") or [])[:T_MAX]
    alarms = rule_alarms(steps)
    hit = {alarm["rule"] for alarm in alarms}
    rows = step_features({"steps": steps})

    no_verify = "no_verify" in hit
    delta = "delta" in hit
    dup2 = "dup2" in hit
    error = "error" in hit
    blind = "blind" in hit
    strict = bool(hit & set(STRICT_RULES))
    return {
        "no_verify": no_verify,
        "delta": delta,
        "dup": any(r["is_dup"] for r in rows),
        "dup2": dup2,
        "error": error,
        "long_gap": "long_gap" in hit,
        "unverified_write": "unverified_write" in hit,
        "blind": blind,
        "strict": strict,
        "full": bool(hit),
        # 兼容旧输出
        "tier1": no_verify or delta,
        "tier1_dup2": no_verify or delta or dup2,
        "tier_all": bool(hit),
    }


def main():
    clean = load_clean(ROOT / "data/raw_v1/run_traces", ROOT / "data/labels/healthy.csv")
    split_path = ROOT / "experiments/splits/task_split_v1.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    test_tasks = split["test_tasks"]
    calibration_tasks = split["calibration_tasks"]

    test = [t for t in clean if t["task"] in test_tasks]
    calibration_all = [t for t in clean if t["task"] in calibration_tasks]

    # 生成一次脚本负样本，后面各折重复使用
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
                "trace": trace,
                "onset": onset,
                "final_ok": final_ok(trace),
            })

    print(f"test traces={len(test)}  calibration traces={len(calibration_all)}  scripted={len(scripted)}")
    print()

    # 简单规则：不需要校准
    print("=== 简单规则（无需校准） ===")
    for rule in ("no_verify", "delta", "dup", "dup2", "error",
                 "long_gap", "unverified_write", "blind",
                 "tier1", "tier1_dup2", "strict", "full"):
        clean_hits = sum(1 for t in test if static_rules(t)[rule])
        print(f"{rule:12} clean 误报={clean_hits}/{len(test)} = {clean_hits / len(test):.1%}")
        for variant_name in VARIANTS:
            items = [s for s in scripted if s["variant"] == variant_name]
            if not items:
                continue
            hits = sum(1 for s in items if static_rules(s["trace"])[rule])
            print(f"    {variant_name:14} {hits}/{len(items)}")
    print()

    # 5 折校准
    rng = random.Random(12345)
    tasks = sorted(calibration_tasks)
    rng.shuffle(tasks)
    folds = [tasks[i::N_FOLDS] for i in range(N_FOLDS)]

    results = {q: {"far": [], "det": {v: [] for v in VARIANTS}} for q in QS}

    for fold_idx in range(N_FOLDS):
        held = set(folds[fold_idx])
        cal_tasks = [t for t in calibration_tasks if t not in held]
        cal_traces = [t for t in calibration_all if t["task"] in cal_tasks]

        for q in QS:
            pool, _, trace_thr = make_calibrator(cal_traces, q)
            far = sum(1 for t in test if max(score_trace(t, pool)) > trace_thr) / len(test)
            results[q]["far"].append(far)
            for variant_name in VARIANTS:
                items = [s for s in scripted if s["variant"] == variant_name]
                if not items:
                    continue
                hits = sum(
                    1 for s in items
                    if max(score_trace(s["trace"], pool)) > trace_thr
                )
                results[q]["det"][variant_name].append(hits / len(items))

    print("=== 5 折校准 ===")
    for q in QS:
        far = results[q]["far"]
        print(f"q={q:.2f}  clean FAR mean={statistics.mean(far):.1%} "
              f"range={min(far):.1%}-{max(far):.1%}")
        for variant_name, vals in results[q]["det"].items():
            print(f"    {variant_name:14} mean={statistics.mean(vals):.0%} "
                  f"range={min(vals):.0%}-{max(vals):.0%}")


if __name__ == "__main__":
    main()
