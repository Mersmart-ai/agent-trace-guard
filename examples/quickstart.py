"""读取一条归档 trace，打印审计标签。

从项目根目录运行：
    python examples/quickstart.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fbs.data.audit import classify_run

trace_path = Path("data/raw_v1/run_traces/task_0001/r01.json")
trace = json.loads(trace_path.read_text(encoding="utf-8"))
row = classify_run(trace)
print(row["run_id"], row["healthy_class"], row["env_invalid_reason"] or "")
