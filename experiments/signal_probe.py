"""0 元信号体检：在 clean trace 上注入已知偏离，看步级特征能否区分。

不调用模型、不跑任务、不改 data/raw_v1。
用法（项目根目录）：

    PYTHONPATH=src python experiments/signal_probe.py

两个关键设计：
1. 参考分布按“动作类型（kind）”分组，而不是按步号对齐：
   同一个 t 在不同任务里可能是读、写、测试或 finish，按 t 比会把
   “步骤角色不同”误当成异常。
2. 多维特征用 Fisher 合并每列的尾概率，而不是取 max：
   max 会被一条长尾特征（如 result_len）绑架，实测几乎全漏。

这是特征灵敏度检查，不是真实检测效果的证据。
"""
import argparse
import copy
import csv
import json
import math
from pathlib import Path

from fbs.actions import tool_kind
from fbs.analysis.features import step_features

# result_len 长尾太重，第一版体检先不放进分数，避免一条特征压掉其余信号
FEATURES = [
    "tested", "fails", "delta_fails", "since_test",
    "since_write", "ok", "is_dup", "repeat_streak",
]
MIN_POOL = 5


def load_clean(traces_root, labels_path):
    labels = {
        r["run_id"]: r["healthy_class"]
        for r in csv.DictReader(open(labels_path, encoding="utf-8"))
    }
    traces = []
    for p in sorted(Path(traces_root).rglob("*.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        if labels.get(t["run_id"]) == "clean_success":
            traces.append(t)
    return traces


def _value(row, feat):
    return float(row[feat])


def build_rows(traces, t_max):
    """每条 trace → 前 t_max 步：kind + 数值向量。"""
    out = []
    for trace in traces:
        rows = []
        for r in step_features(trace)[:t_max]:
            rows.append({
                "kind": r["kind"],
                "vec": {f: _value(r, f) for f in FEATURES},
            })
        out.append(rows)
    return out


def build_pool(clean_rows):
    """按 kind 汇总 clean 的所有步，用于给新步算尾概率。"""
    pool = {}
    for i, rows in enumerate(clean_rows):
        for item in rows:
            pool.setdefault(item["kind"], []).append((i, item["vec"]))
    return pool


def emp_p(x, values):
    """两侧经验尾概率，+1 修正；值在样本范围外时 p 最小。"""
    n = len(values)
    if n == 0:
        return 1.0
    ge = sum(1 for v in values if v >= x)
    le = sum(1 for v in values if v <= x)
    return min(1.0, 2.0 * min((1 + ge) / (n + 1), (1 + le) / (n + 1)))


def fisher(vec, kind, pool, exclude=None):
    """Fisher 合并：每一步得到 Σ -log(p_j)。"""
    total = 0.0
    for f in FEATURES:
        vals = [v[f] for i, v in pool.get(kind, []) if i != exclude]
        if len(vals) < MIN_POOL:
            continue
        total += -math.log(max(emp_p(vec[f], vals), 1e-6))
    return total


def clean_scores_by_trace(clean_rows, pool):
    """每条 clean 的逐步分数（留一法）。"""
    return [
        [fisher(item["vec"], item["kind"], pool, exclude=i) for item in rows]
        for i, rows in enumerate(clean_rows)
    ]


def percentile(values, q):
    vals = sorted(values)
    idx = min(len(vals) - 1, max(0, math.ceil(q * len(vals)) - 1))
    return vals[idx]


def _renumber(steps):
    for i, h in enumerate(steps, 1):
        h["step"] = i
    return steps


# ---------- 扰动 ----------

def drop_verify(trace):
    """删掉最后一次 run_tests：模拟“没主动验证就交差”。"""
    steps = copy.deepcopy(trace["steps"])
    idx = max((i for i, h in enumerate(steps) if h.get("tool") == "run_tests"), default=None)
    if idx is None:
        return None
    onset = idx + 1
    del steps[idx]
    return {"steps": _renumber(steps)}, onset


def repeat_read(trace):
    """把第一次读操作重复 4 次：模拟打转。"""
    steps = copy.deepcopy(trace["steps"])
    idx = next((i for i, h in enumerate(steps) if h.get("tool") in ("read_file", "list_files")), None)
    if idx is None:
        return None
    copies = [copy.deepcopy(steps[idx]) for _ in range(4)]
    steps[idx + 1:idx + 1] = copies
    return {"steps": _renumber(steps)}, idx + 2


def write_no_test(trace):
    """插入一次没有 test_state 的写：模拟强制判分失效。"""
    steps = copy.deepcopy(trace["steps"])
    idx = next((i for i, h in enumerate(steps) if tool_kind(h) == "write"), None)
    if idx is None:
        return None
    h = copy.deepcopy(steps[idx])
    h["test_state"] = None
    h["judge"] = None
    steps.insert(idx + 1, h)
    return {"steps": _renumber(steps)}, idx + 2


def regression_after_green(trace):
    """把第二次全过的测试改成红：模拟改坏又修好（absorbed error）。"""
    steps = copy.deepcopy(trace["steps"])
    idxs = [i for i, h in enumerate(steps) if h.get("test_state") == []]
    if len(idxs) < 2:
        return None
    idx = idxs[1]
    steps[idx]["test_state"] = ["probe_test"]
    return {"steps": _renumber(steps)}, idx + 1


def extra_writes(trace):
    """把第一次写重复 3 次：模拟反复改同一处。"""
    steps = copy.deepcopy(trace["steps"])
    idx = next((i for i, h in enumerate(steps) if tool_kind(h) == "write"), None)
    if idx is None:
        return None
    copies = [copy.deepcopy(steps[idx]) for _ in range(3)]
    steps[idx + 1:idx + 1] = copies
    return {"steps": _renumber(steps)}, idx + 2


VARIANTS = {
    "drop_verify": drop_verify,
    "repeat_read": repeat_read,
    "write_no_test": write_no_test,
    "regression_after_green": regression_after_green,
    "extra_writes": extra_writes,
}


def evaluate(fn, clean_traces, pool, step_thr, trace_thr, t_max):
    out = []
    for i, trace in enumerate(clean_traces):
        made = fn(trace)
        if made is None:
            continue
        new_trace, onset = made
        rows = build_rows([new_trace], t_max)[0]
        if onset > len(rows) or onset > t_max:
            continue
        step_alarm = None
        trace_alarm = None
        per_feature = {f: 1.0 for f in FEATURES}
        for t in range(onset, len(rows) + 1):
            item = rows[t - 1]
            s = fisher(item["vec"], item["kind"], pool, exclude=i)
            if s > step_thr and step_alarm is None:
                step_alarm = t
            if s > trace_thr and trace_alarm is None:
                trace_alarm = t
            for f in FEATURES:
                vals = [v[f] for j, v in pool.get(item["kind"], []) if j != i]
                if len(vals) >= MIN_POOL:
                    per_feature[f] = min(per_feature[f], emp_p(item["vec"][f], vals))
        out.append({
            "step_alarm": step_alarm,
            "trace_alarm": trace_alarm,
            "onset": onset,
            "p": per_feature,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", default="data/raw_v1/run_traces")
    ap.add_argument("--labels", default="data/labels/healthy.csv")
    ap.add_argument("--t-max", type=int, default=8)
    ap.add_argument("--quantile", type=float, default=0.9)
    args = ap.parse_args()

    clean_traces = load_clean(args.traces, args.labels)
    clean_rows = build_rows(clean_traces, args.t_max)
    pool = build_pool(clean_rows)
    by_trace = clean_scores_by_trace(clean_rows, pool)

    all_steps = [s for row in by_trace for s in row]
    step_thr = percentile(all_steps, args.quantile)
    trace_thr = percentile([max(row) for row in by_trace], args.quantile)

    print(f"clean traces: {len(clean_traces)}  t_max: {args.t_max}")
    print("pool sizes:", {k: len(v) for k, v in sorted(pool.items())})
    print(f"step threshold (q={args.quantile}): {step_thr:.2f}")
    print(f"trace threshold (max, q={args.quantile}): {trace_thr:.2f}")
    print(f"clean 步级误报：{sum(s > step_thr for s in all_steps) / len(all_steps):.1%}")
    print(f"clean 轨迹误报@step阈值：{sum(max(row) > step_thr for row in by_trace) / len(by_trace):.1%}")
    print(f"clean 轨迹误报@trace阈值：{sum(max(row) > trace_thr for row in by_trace) / len(by_trace):.1%}")
    print()

    for name, fn in VARIANTS.items():
        res = evaluate(fn, clean_traces, pool, step_thr, trace_thr, args.t_max)
        if not res:
            print(f"{name}: 没有可用样本")
            continue
        step_flagged = [r for r in res if r["step_alarm"] is not None]
        trace_flagged = [r for r in res if r["trace_alarm"] is not None]
        step_delays = sorted(r["step_alarm"] - r["onset"] for r in step_flagged)
        trace_delays = sorted(r["trace_alarm"] - r["onset"] for r in trace_flagged)
        print(f"{name:24} n={len(res):2d}  "
              f"step={len(step_flagged) / len(res):3.0%} (delay={step_delays[0] if step_delays else '-'})  "
              f"trace={len(trace_flagged) / len(res):3.0%} (delay={trace_delays[len(trace_delays) // 2] if trace_delays else '-'})")
        hits = {
            f: sum(1 for r in res if r["p"][f] <= 0.05) / len(res)
            for f in FEATURES
        }
        print("    per-feature p<=0.05: "
              + "  ".join(f"{f}={v:.0%}" for f, v in hits.items() if v > 0))


if __name__ == "__main__":
    main()
