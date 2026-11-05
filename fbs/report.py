"""报告层：把 trace.json 变成可读的表 / 一行 CSV / 归因结果。

之前这些东西都散在临时脚本里，跑一次删一次。
现在统一在这里，三个入口：

    python -m fbs.report                 出总表（分布 + 每条明细）
    python -m fbs.report --csv runs.csv   导出 CSV（给数据分析用）
    python -m fbs.report --run xxx_r01    看一条的详情（含 regressions）

判断"这一步有没有改文件"放在 is_write，因为 bash 也能写文件，
只数 write_file 会把 "echo > a.py" 当成没动手。
"""

import csv
import json
import re
import sys
from pathlib import Path

from fbs.actions import is_write, tool_kind
from fbs.classify import classify
from fbs.locate import build_states, locate, regressions, render

def summarize(trace):
    """一条 trace → 一行结构化数据。字段对齐数据分析那边要的 CSV。"""
    steps = trace["steps"]
    states = build_states(steps)

    kinds = {}
    for h in steps:
        k = tool_kind(h)
        kinds[k] = kinds.get(k, 0) + 1

    return {
        "run_id": trace["run_id"],
        "task_id": trace.get("task", trace["run_id"].rsplit("_r", 1)[0]),
        "ts": trace.get("ts", ""),
        "status": "pass" if trace.get("reason") == "right exit" else "fail",
        "reason": trace.get("reason", ""),
        "failure_category": classify(steps, trace.get("reason", "")),
        "turns": len(steps),
        "n_write": kinds.get("write", 0),
        "n_read": kinds.get("read", 0),
        "n_navigate": kinds.get("navigate", 0),
        "n_verify": kinds.get("verify", 0),
        "n_regressions": len(regressions(states)),
        "shape": render(states),
    }


def _load_all(root="run_traces"):
    out = []
    for p in sorted(Path(root).rglob("*.json")):
        out.append((p, json.loads(p.read_text(encoding="utf-8"))))
    return out


def _print_table(rows):
    from collections import Counter

    print(f"共 {len(rows)} 条\n")

    print("=== 失败类型 ===")
    c = Counter(r["failure_category"] for r in rows)
    top = max(c.values()) if c else 1
    for k in ["pass", "wrong_fix", "gave_up", "stuck", "no_verify", "timeout", "other"]:
        n = c.get(k, 0)
        print(f"  {k:<12} {n:>3}  {'█' * int(n / top * 28)}")

    print("\n=== 动作分布（平均每条）===")
    for key, label in [("n_write", "写"), ("n_read", "读"), ("n_navigate", "导航"), ("n_verify", "验证")]:
        avg = sum(r[key] for r in rows) / len(rows)
        print(f"  {label:<4} {avg:>5.1f} 步")

    print("\n=== 明细 ===")
    print(f"  {'run_id':<26}{'类别':<12}{'步数':>4}{'写':>4}{'读':>4}{'验证':>4}{'回退':>4}")
    for r in rows:
        print(f"  {r['run_id']:<26}{r['failure_category']:<12}{r['turns']:>4}"
              f"{r['n_write']:>4}{r['n_read']:>4}{r['n_verify']:>4}{r['n_regressions']:>4}")


def _print_one(path, trace):
    steps = trace["steps"]
    states = build_states(steps)
    print(f"{trace['run_id']}  {len(steps)} 步  {render(states)}")
    print(f"  reason      = {trace.get('reason')}")
    print(f"  locate      = {locate(states)}")
    print(f"  regressions = {regressions(states)}")
    print()
    print(f"  {'步':>3} {'工具':<11}{'动作':<9}{'判据':<7}命令/路径")
    for h in steps:
        a = h.get("args") or {}
        ts = h.get("test_state")
        judge = "-" if ts is None else ("全过" if ts == [] else f"{len(ts)}红")
        cmd = a.get("command") or ""
        cmd_first = cmd.splitlines()[0] if cmd.splitlines() else ""
        detail = (a.get("path") or a.get("pattern") or cmd_first)[:55]
        print(f"  {h['step']:>3} {h['tool']:<11}{tool_kind(h):<9}{judge:<7}{detail}")


def main(argv):
    if "--run" in argv:
        key = argv[argv.index("--run") + 1]
        for p, t in _load_all():
            if t["run_id"] == key:
                _print_one(p, t)
                return
        print(f"找不到 {key}")
        return

    rows = [summarize(t) for _, t in _load_all()]

    if "--csv" in argv:
        out = Path(argv[argv.index("--csv") + 1])
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"写了 {len(rows)} 行到 {out}")
        return

    _print_table(rows)


if __name__ == "__main__":
    main(sys.argv[1:])
