"""旧版的离线批处理，已经被 __main__ 取代，保留下来备用。

不需要 API：用 fixed_policy 假装模型，把每个任务的代码原样读一遍再写回去，
然后跑测试看退出码。用来验证 workspace 复制和 pytest 调用是否正常。

要跑的话：python legacy.py
"""
import sys
from pathlib import Path

# 允许直接 `python scripts/legacy_fixed_policy.py` 运行（不必先 pip install -e .）
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fbs.agent.tools import read_file, run_tests, write_file
from fbs.data.trace import prepare_workspace


def fixed_policy(step, history):
    """
    假大脑，不调模型。
    0 读文件，1 写文件，2 跑测试，3 及以上结束。
    """
    if step == 0:
        return {"tool": "read_file", "args": {"path": "calc.py"}}
    if step == 1:
        content = history[0]["result"]
        fixed = content.replace("old", "new")
        return {"tool": "write_file", "args": {"path": "calc.py", "content": fixed}}
    if step == 2:
        return {"tool": "run_tests", "args": {}}
    return {"tool": "finish", "args": {}}


def run_agent():
    """把 tasks/ 下每个任务的代码原样读写一遍，然后跑测试。"""
    results = {}
    for task in sorted(Path("tasks").iterdir()):
        workspace = prepare_workspace(task, Path("runs") / task.name)
        if workspace is None:
            continue
        root = Path(workspace).resolve()
        for f in sorted(root.rglob("*")):
            if not f.is_file():
                continue
            if "__pycache__" in f.parts:
                continue
            if f.suffix != ".py":
                continue
            rel = f.relative_to(root)
            content = read_file(workspace, rel).replace("\r", "")
            write_file(workspace, rel, content)
        results[task.name] = run_tests(workspace, Path(task / "tests"))
    print(results)

    if any(r.get("exit_code") != 0 for r in results.values()):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    run_agent()
