"""把 dsh 的 session JSONL 事件映射成我们的 step history，并跑规则监控。

用法：

    .venv/Scripts/python.exe experiments/dsh_adapter.py \
        data/dsh/events_web.jsonl --session session-xxxx

dsh 的结果文本有两个坑：

1. `isError` 只表示“工具调用本身失败”；命令的非零退出码写在文本里
   （`[exit code: 1]`），所以这里单独解析并存进 `step["exit_code"]`。
2. PowerShell 会把子进程的 stderr 包成 NativeCommandError，导致 pytest
   明明 `6 passed`，整条命令仍以 exit code 1 结束。所以测试步以 pytest
   输出为准，不看退出码。

默认 `ok` 对齐本家 harness：只看 `isError`。加 `--strict-exit` 后，
非测试步的退出码非 0 也算失败，用于对比实验。
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fbs.agent.judge import NO_CASE
from fbs.analysis.monitor import rule_alarms

# 这些命令只是查找可执行文件，里面出现的 pytest 不是一次测试。
PS_LOOKUP_CMDS = {
    "get-command", "get-childitem", "get-help", "get-item", "where", "which",
}

# PowerShell 里会改文件系统的 cmdlet；`>` / `>>` 另外判。
PS_WRITE_CMDS = {
    "set-content", "add-content", "clear-content", "out-file", "tee-object",
    "new-item", "remove-item", "copy-item", "move-item", "rename-item",
    "set-item", "set-itemproperty", "new-itemproperty", "remove-itemproperty",
}

# 只认 pytest 的调用形式，避免把 `Get-ChildItem -Filter 'pytest.exe'`
# 这种查找命令误判成跑测试。
PYTEST_CMD = re.compile(r"(?<![\w-])pytest(?:\.exe)?\s+(?:-{1,2}\w|tests?\b)")
# `pytest --version` / `--help` / `--collect-only` 不是验证，不能重置 since_test。
PYTEST_INFO = re.compile(r"pytest(?:\.exe)?\s+(?:--version|--help|-h|--collect-only)\b")
PS_REDIRECT = re.compile(r"(?<![\d&])>{1,2}(?!&)")
EXIT_CODE = re.compile(r"\[\s*exit code:\s*(-?\d+)\s*\]")
FAILED_LINE = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)")
PASSED_COUNT = re.compile(r"\b\d+ passed\b")
FAILED_COUNT = re.compile(r"\b\d+ (?:failed|errors?)\b")


def load_events(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def latest_session(rows):
    by = {}
    for row in rows:
        by.setdefault(row.get("session"), []).append(row)
    return max(by, key=lambda sid: by[sid][-1].get("ts"))


def events_of(rows, session):
    return [row["event"] for row in rows if row.get("session") == session]


def result_for(events, call_id):
    """dsh 的 tool/result 把 callId 放在 data.message 里。"""
    for event in events:
        if event.get("type") != "tool/result":
            continue
        data = event.get("data") or {}
        message = data.get("message") or {}
        if message.get("toolCallId") == call_id or (message.get("source") or {}).get("callId") == call_id:
            text = "\n".join(
                part.get("text", "")
                for part in (message.get("content") or [])
                if isinstance(part, dict)
            )
            return text, bool(message.get("isError"))
    return "", False


def parse_exit_code(text):
    """取最后一个 `[exit code: N]`；没有返回 None。"""
    marks = EXIT_CODE.findall(text or "")
    return int(marks[-1]) if marks else None


def parse_test_state(text, exit_code=None):
    """从 pytest 输出里提取失败测试。

    []        全过
    [名字]    这些测试失败
    [NO_CASE] 跑了但判不了（pytest 没装上、collection error 等）
    None      没有测试输出
    """
    if not text:
        return None

    names = set()
    for line in text.splitlines():
        match = FAILED_LINE.match(line.strip())
        if match:
            names.add(match.group(1).split(" - ")[0].split("::")[-1])
    if names:
        return sorted(names)

    # PowerShell 的 NativeCommandError 会让成功的 pytest 也 exit 1，
    # 所以有 "N passed" 且没有失败计数时，先信输出。
    if PASSED_COUNT.search(text) and not FAILED_COUNT.search(text):
        return []
    if exit_code == 0:
        return []
    if exit_code is None:
        return None
    return [NO_CASE]


def is_test_command(command):
    """是不是真的在跑 pytest（而不是查找、看版本或只看 collection）。"""
    for seg in re.split(r"\|\||&&|[|;]", command):
        words = seg.strip().split()
        # Get-Command python,py,pytest 这类查找命令里 pytest 只是参数
        if words and words[0].lower() in PS_LOOKUP_CMDS:
            continue
        if PYTEST_INFO.search(seg):
            continue
        if "-m pytest" in seg or PYTEST_CMD.search(seg):
            return True
    return False


def is_pwsh_write(command):
    """PowerShell 命令有没有改文件系统。"""
    if PS_REDIRECT.search(command):
        return True
    for seg in re.split(r"\|\||&&|[|;]", command):
        words = seg.strip().split()
        if words and words[0].lower() in PS_WRITE_CMDS:
            return True
    return False


def map_step(event, events, strict_exit=False):
    data = event.get("data") or {}
    name = data.get("name")
    call_id = data.get("callId")
    try:
        args = json.loads(data.get("arguments") or "{}")
    except json.JSONDecodeError:
        args = {}
    text, is_error = result_for(events, call_id)
    exit_code = parse_exit_code(text)

    if name == "read":
        tool = "read_file"
    elif name in ("edit", "write"):
        tool = "write_file"
        # edit 用 old_string/new_string，write 用 content；
        # 都保留成 content，否则同一文件的不同编辑在 dup2 眼里会变成同一个动作。
        content = args.get("new_string", "") if name == "edit" else args.get("content", "")
        args = {"path": args.get("file_path", ""), "content": content}
    elif name == "glob":
        tool = "list_files"
    elif name == "grep":
        tool = "grep"
    elif name == "pwsh":
        command = args.get("command", "")
        if is_test_command(command):
            tool = "run_tests"
        elif is_pwsh_write(command):
            tool = "write_file"
            args = {"command": command}
        else:
            tool = "bash"
    else:
        tool = name or "other"

    if tool == "run_tests":
        test_state = parse_test_state(text, exit_code)
    else:
        test_state = None

    # 测试步的“红”是信号，不是工具错误；跑不起来由 test_state=[NO_CASE] 表达。
    if strict_exit and tool != "run_tests":
        ok = not is_error and exit_code in (None, 0)
    else:
        ok = not is_error

    return {
        "step": None,
        "tool": tool,
        "args": args,
        "result": text,
        "ok": ok,
        "test_state": test_state,
        "judge": "dsh",
        "exit_code": exit_code,
    }


def map_history(rows, session=None, strict_exit=False):
    session = session or latest_session(rows)
    events = events_of(rows, session)
    history = []
    for event in events:
        if event.get("type") != "tool/call":
            continue
        step = map_step(event, events, strict_exit=strict_exit)
        step["step"] = len(history) + 1
        history.append(step)
    return session, history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("events", nargs="?", default="data/dsh/events_web.jsonl")
    ap.add_argument("--session", default=None)
    ap.add_argument("--strict-exit", action="store_true",
                    help="非测试步退出码非 0 也算失败")
    args = ap.parse_args()

    rows = load_events(args.events)
    session, history = map_history(rows, args.session, strict_exit=args.strict_exit)
    print(f"session={session} steps={len(history)}")
    for step in history:
        print(
            f"  {step['step']:2d} {step['tool']:11} ok={int(step['ok'])} "
            f"exit={step['exit_code']} state={step['test_state']}"
        )
    print("tool counts:", dict(Counter(step["tool"] for step in history)))
    print("alarms:", rule_alarms(history))


if __name__ == "__main__":
    main()
