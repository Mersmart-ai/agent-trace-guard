"""0 元信号体检：在 clean trace 上注入已知偏离，看步级特征能否区分。

不调用模型、不跑任务、不改 data/raw_v1。
用法（任何目录都可以）：

    python experiments/signal_probe.py

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
import sys
from pathlib import Path

# 允许直接 `python experiments/signal_probe.py` 运行：
# 把项目根目录下的 src/ 加进 import 路径，不依赖 PYTHONPATH
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from fbs.actions import tool_kind
from fbs.analysis.features import step_features

# result_len 长尾太重，第一版体检先不放进分数，避免一条特征压掉其余信号
FEATURES = [
    "tested", "fails", "delta_fails", "since_test",
    "since_write", "n_verify", "ok", "is_dup", "repeat_streak",
]
MIN_POOL = 5


def load_clean(traces_root, labels_path):
    """按冻结标签挑出 clean_success 的 trace。

    :param traces_root: trace 根目录，str 或 Path；
                        来源：main() 的 --traces，默认 "data/raw_v1/run_traces"；
                        目录结构是 <task>/rNN.json，一个文件一条 trace
    :param labels_path: 审计标签 CSV，str 或 Path；
                        来源：main() 的 --labels，默认 "data/labels/healthy.csv"；
                        由 `python -m fbs.data.audit` 生成，一行一条 trace
    :return: list[dict]，只含 healthy_class == "clean_success" 的 trace；
             每个 dict 是 json.loads 后的完整 trace，形如
             {"run_id": "task_0001_r01", "task": "task_0001", "ts": ...,
              "reason": ..., "steps": [{"step": 1, "tool": ...}, ...]}
             读取顺序固定（sorted），同一份数据每次返回顺序一致

    连接方式：CSV 的 run_id 列 == JSON 里的 "run_id" 字段。
    不按文件路径或行号连接，因为两边顺序没有保证。

    数据来源：
      traces_root ← data/raw_v1/run_traces/（冻结归档，只读）
      labels_path ← data/labels/healthy.csv（audit 产物）

    查不到的 run_id 会被静默跳过；本函数不校验 schema。
    """
    # CSV 一行一条 trace；r 是其中一行（dict），这里压成 run_id -> 标签 的查询表
    labels = {
        r["run_id"]: r["healthy_class"]
        for r in csv.DictReader(open(labels_path, encoding="utf-8"))
    }

    traces = []
    # p 是一个 JSON 路径；t 是这条 trace 的完整 dict
    for p in sorted(Path(traces_root).rglob("*.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        # 只用 clean_success 当正常参考；env_invalid / task_failure 都不进来
        if labels.get(t["run_id"]) == "clean_success":
            traces.append(t)
    return traces


def _value(row, feat):
    """把一步里的一个特征转成 float。

    step_features 返回的 tested / ok / is_dup 是 bool，其余是 int；
    统一成 float，后面算中位数、尾概率时不用再分支。
    单独留一个函数，是为了以后加变换（比如 result_len 的 log1p）
    只改这里，不动 build_rows。
    """
    return float(row[feat])


def build_rows(traces, t_max):
    """每条 trace → 前 t_max 步：kind + 数值向量。

    :param traces: list[dict]，load_clean 的返回值，一条 trace 一个 dict
    :param t_max: int，只取前 t_max 步；main 里默认 8
    :return: list[list[dict]]，外层一条 trace，内层一步，形如
             [{"kind": "read",
               "vec": {"tested": 0.0, "fails": 0.0, "delta_fails": 0.0, ...}},
              ...]
             内层长度 = min(trace 步数, t_max)，不补零

    为什么带 kind：
      参考分布按动作类型分组；kind 是分组键，不参与数值打分。
    为什么截断到 t_max：
      t>8 的 clean 样本太少（n_t<=12），没有可靠校准参考。
    为什么不补零：
      不同轨迹长度不同，补零会造出假的"第 9 步"，把长度差异混进分数。
    """
    out = []
    for trace in traces:
        # 先算全部步再切片：step_features 没有 t_max 参数。
        # 对 60 步的 trace 会多算 52 步，纯 Python 成本可忽略。
        rows = []
        for r in step_features(trace)[:t_max]:
            rows.append({
                "kind": r["kind"],
                "vec": {f: _value(r, f) for f in FEATURES},
            })
        out.append(rows)
    return out


def build_pool(clean_rows):
    """按 kind 汇总 clean 的所有步，用于给新步算尾概率。

    :param clean_rows: list[list[dict]]，build_rows 的返回值：
                       外层一条 clean trace，内层一步 {kind, vec}
    :return: dict[str, list[tuple[int, dict]]]
             键是 kind（navigate/read/write/verify/other），
             值是 [(trace 下标, 这一步的 vec), ...]
             例如 {"read": [(0, {...}), (3, {...}), ...], ...}

    为什么按 kind 分组：
      同一个步号 t 在不同任务里角色不同（第 3 步可能是读、写或 finish），
      按 t 对齐会把"角色不同"误当成异常。按 kind 分组后，
      新的一步只和同类动作比。

    为什么存 trace 下标 i：
      留一法要用。给第 i 条 clean 打分时，把它自己的步从参考池里排除；
      不排除的话，它自己会把分布拉向自己，分数偏小。

    注意：
      - 同一条 trace 的多个同类步都会进池，池内样本不独立
      - 池子跨任务混合，没有按任务身份分组；任务基线差异可能造成误报
    """
    pool = {}
    for i, rows in enumerate(clean_rows):
        for item in rows:
            # 没有这个 kind 就先建空列表，再追加
            pool.setdefault(item["kind"], []).append((i, item["vec"]))
    return pool


def emp_p(x, values):
    """单特征的两侧经验尾概率。

    :param x: 待判断的数值（一步里的某个特征，比如 since_test=3）
    :param values: 参考样本，同类动作的 clean 步在该特征上的取值列表
    :return: float，范围 (0, 1]；值越极端返回越小；样本为空时返回 1.0

    公式：
        ge = 参考样本里 >= x 的个数
        le = 参考样本里 <= x 的个数
        p = min(1, 2 * min((1+ge)/(n+1), (1+le)/(n+1)))

    为什么要 +1：
      不加的话，落在样本范围外的值会得到 p=0，
      下一步 -log(p) 直接变成无穷。加了 +1 后，最小 p = 2/(n+1)，
      n 越大，分辨率越细。

    为什么两侧：
      我们不知道异常是偏大还是偏小（比如 since_test 太大是盲写，
      fails 太小可能是没测），所以两边都看，取更极端的一侧再乘 2。

    注意：
      这是特征级的经验尾概率，不是最终的 conformal p 值。
      最终的误报控制靠后面在 clean 分数上定的阈值。
    """
    n = len(values)
    if n == 0:
        return 1.0
    ge = sum(1 for v in values if v >= x)  # 比 x 大的（含等于）
    le = sum(1 for v in values if v <= x)  # 比 x 小的（含等于）
    # 取更极端的一侧，乘 2 变成两侧；p 不能超过 1
    return min(1.0, 2.0 * min((1 + ge) / (n + 1), (1 + le) / (n + 1)))


def fisher(vec, kind, pool, exclude=None):
    """把一步的多个特征 p 值合并成一个分数。

    :param vec: 当前步的数值向量，{特征名: float}
    :param kind: 当前步的动作类型，决定去哪个池子取参考值
    :param pool: build_pool 的返回值，kind -> [(trace 下标, vec), ...]
    :param exclude: 要排除的 trace 下标（留一法）；None 表示不排除
    :return: float，Σ -log(p_j)；越大越异常

    为什么用 -log(p)：
      p 越小越异常，但直接相加没有意义（p=0.01 比 p=0.5 小，贡献反而小）。
      -log(p) 把"小 p"变成"大分数"：p=1 -> 0，p=0.03 -> 3.5。

    为什么加总而不是取最大：
      取最大会被一条长尾特征绑架（实测 result_len 会把阈值抬高）。
      加总让多个中等偏离也能累积成高分。

    注意：
      这不是教科书里的 Fisher 检验（不查卡方分布）。
      这里只是借用"Σ -log(p)"这个合并方式；
      阈值靠 clean 轨迹的分数分布定，见 percentile / evaluate。
    """
    total = 0.0
    for f in FEATURES:
        # 同类动作的 clean 值；exclude 掉自己这条 trace
        vals = [v[f] for i, v in pool.get(kind, []) if i != exclude]
        if len(vals) < MIN_POOL:
            continue
        # 小 p -> 大分数；1e-6 只是防御，emp_p 本身不会返回 0
        total += -math.log(max(emp_p(vec[f], vals), 1e-6))
    return total


def clean_scores_by_trace(clean_rows, pool):
    """给每条 clean trace 算逐步分数，用来定阈值。

    :param clean_rows: build_rows 的返回值
    :param pool: build_pool 的返回值
    :return: list[list[float]]，外层一条 trace，内层每一步的 Fisher 分数

    为什么用 exclude=i：
      留一法。给第 i 条 clean 打分时，参考池里不能有它自己的步；
      否则它会把自己拉向正常，分数偏小，阈值被压低。
    """
    all_scores = []

    # 外层：一条 clean trace
    for trace_index, step_rows in enumerate(clean_rows):
        one_trace_scores = []

        # 内层：这条 trace 的每一步
        for item in step_rows:
            score = fisher(item["vec"], item["kind"], pool, exclude=trace_index)
            one_trace_scores.append(score)

        all_scores.append(one_trace_scores)

    return all_scores


def percentile(values, q):
    """取经验分位数，不插值。

    :param values: list[float]
    :param q: 0 到 1，例如 0.9 表示 90 分位
    :return: 排序后第 ceil(q*n) 个值（从 1 开始数）；越界时取两端

    例：values=[1,2,3,4]，q=0.9 -> ceil(3.6)=4 -> 返回第 4 个，也就是 4。
    不插值是因为阈值要落在真实观测值上，方便解释和复现。
    """
    vals = sorted(values)
    n = len(vals)
    if n == 0:
        raise ValueError("percentile() 需要至少一个值")

    # 想要的名次（从 1 开始数）
    rank = math.ceil(q * n)

    # 换成 Python 下标（从 0 开始）
    index = rank - 1

    # q=0 或 q=1 时可能越界，夹到两端
    if index < 0:
        index = 0
    if index >= n:
        index = n - 1

    return vals[index]


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


# 只放 harness 允许的偏离。
# "写后没有 test_state" 在当前 loop 里不可能发生（写后强制判分），
# 那属于数据层的不变量检查，不是 agent 行为异常，所以不放进这里。
VARIANTS = {
    "drop_verify": drop_verify,
    "repeat_read": repeat_read,
    "regression_after_green": regression_after_green,
    "extra_writes": extra_writes,
}


def evaluate(fn, clean_traces, pool, step_thr, trace_thr, t_max):
    """对每条 clean 施加一种扰动，看扰动后能不能报警。

    :param fn: 扰动函数，输入 trace，返回 (新 trace, onset) 或 None
    :param clean_traces: load_clean 的返回值
    :param pool: build_pool 的返回值
    :param step_thr: 步级阈值
    :param trace_thr: 轨迹级阈值
    :param t_max: 只看前 t_max 步
    :return: list[dict]，每条可用 trace 一项：
             step_alarm   第一次超过步级阈值的步号，None 表示没报
             trace_alarm  第一次超过轨迹阈值的步号，None 表示没报
             onset        扰动发生的步号
             p            各特征在扰动后最极端的一次 p 值

    为什么从 onset 开始扫：
      扰动之前的行为是正常的，扫前面会人为制造"提前报警"。
    为什么 exclude=i：
      扰动版本来自第 i 条 clean，参考池里要排掉原 trace。
    """
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
    # 默认路径相对项目根目录，不依赖当前工作目录
    ap.add_argument("--traces", default=str(ROOT / "data/raw_v1/run_traces"))
    ap.add_argument("--labels", default=str(ROOT / "data/labels/healthy.csv"))
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
