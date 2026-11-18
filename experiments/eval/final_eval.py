"""规则监控最终评估：80 条归档 trace + 12 条真实 trace。

用法：

    .venv/Scripts/python.exe experiments/final_eval.py
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from fbs.analysis.monitor import rule_alarms, strict_alarms


def load_labels():
    path = ROOT / "data" / "labels" / "healthy.csv"
    return {
        r["run_id"]: r["healthy_class"]
        for r in csv.DictReader(path.open(encoding="utf-8"))
    }


def evaluate(trace, cls):
    alarms = rule_alarms(trace.get("steps") or [])
    strict = strict_alarms(alarms)
    return {
        "class": cls,
        "all": alarms,
        "strict": strict,
        "rules": [a["rule"] for a in alarms],
        "strict_rules": [a["rule"] for a in strict],
    }


def main():
    labels = load_labels()
    rows = []
    for path in sorted((ROOT / "data" / "raw_v1" / "run_traces").rglob("*.json")):
        trace = json.loads(path.read_text(encoding="utf-8"))
        cls = labels.get(trace["run_id"], "unknown")
        rows.append((trace["run_id"], evaluate(trace, cls)))

    print("=== raw_v1（80 条）===")
    by_class = defaultdict(list)
    for _, row in rows:
        by_class[row["class"]].append(row)

    for cls in sorted(by_class):
        items = by_class[cls]
        strict_hits = sum(1 for x in items if x["strict"])
        full_hits = sum(1 for x in items if x["all"])
        rules = Counter(r for x in items for r in x["strict_rules"])
        print(
            f"{cls:24} n={len(items):2d}  strict={strict_hits:2d}/{len(items):2d}  "
            f"full={full_hits:2d}/{len(items):2d}  strict_rules={dict(rules)}"
        )

    clean = [x for x in rows if x[1]["class"] == "clean_success"]
    clean_strict = sum(1 for _, x in clean if x["strict"])
    clean_full = sum(1 for _, x in clean if x["all"])
    print()
    print(f"clean_success 误报：strict={clean_strict}/{len(clean)}  full={clean_full}/{len(clean)}")
    if clean_full:
        names = Counter(r for _, x in clean for r in x["rules"])
        print("clean 命中的规则：", dict(names))

    print()
    print("=== real（真实模型 trace）===")
    real_rows = []
    for path in sorted((ROOT / "data" / "traces" / "real").rglob("*.json")):
        trace = json.loads(path.read_text(encoding="utf-8"))
        real_rows.append((trace["run_id"], evaluate(trace, "real")))
    for run_id, row in real_rows:
        print(f"{run_id:36} strict={row['strict_rules']}  full={row['rules']}")
    print(
        f"真实 trace 报警：strict={sum(1 for _, x in real_rows if x['strict'])}/{len(real_rows)}  "
        f"full={sum(1 for _, x in real_rows if x['all'])}/{len(real_rows)}"
    )


if __name__ == "__main__":
    main()
