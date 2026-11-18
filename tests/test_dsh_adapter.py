"""dsh 适配器的测试：退出码、测试状态、PowerShell 写操作、step 映射。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fbs.agent.judge import NO_CASE
from experiments.dsh_adapter import (
    is_pwsh_write,
    is_test_command,
    map_history,
    map_step,
    parse_exit_code,
    parse_test_state,
)


def _call(name, arguments, call_id="c1"):
    return {
        "type": "tool/call",
        "data": {
            "name": name,
            "callId": call_id,
            "arguments": json.dumps(arguments),
        },
    }


def _result(text, call_id="c1", is_error=False):
    return {
        "type": "tool/result",
        "data": {
            "message": {
                "toolCallId": call_id,
                "isError": is_error,
                "content": [{"type": "text", "text": text}],
            }
        },
    }


def _map(name, arguments, text, is_error=False, strict_exit=False):
    events = [_call(name, arguments), _result(text, is_error=is_error)]
    return map_step(events[0], events, strict_exit=strict_exit)


def test_parse_exit_code():
    assert parse_exit_code("boom\n[exit code: 1]") == 1
    assert parse_exit_code("[exit code: 0]") == 0
    assert parse_exit_code("no marker") is None
    # 取最后一个
    assert parse_exit_code("[exit code: 1]\n[exit code: 0]") == 0


def test_test_state_passed_despite_exit_one():
    # PowerShell NativeCommandError：pytest 成功，但整条命令 exit 1
    text = "6 passed, 1 warning in 0.02s\n[stderr]\n...[exit code: 1]"
    assert parse_test_state(text, 1) == []


def test_test_state_failed_names():
    text = "FAILED tests/test_calc.py::test_add - AssertionError\n1 failed, 2 passed"
    assert parse_test_state(text, 1) == ["test_add"]


def test_test_state_no_case():
    text = "No module named pytest\n[exit code: 1]"
    assert parse_test_state(text, 1) == [NO_CASE]


def test_test_state_exit_zero_and_empty():
    assert parse_test_state("......", 0) == []
    assert parse_test_state("", 0) is None


def test_is_test_command():
    assert is_test_command("python -m pytest -q")
    assert is_test_command("pytest -q")
    assert is_test_command("uv run --with pytest python -m pytest -q")
    assert not is_test_command(
        "Get-ChildItem -Path $env:USERPROFILE -Filter 'pytest.exe' -Recurse"
    )
    assert not is_test_command("Get-Command python, python3, pytest, py")


def test_is_test_command_ignores_version_help_and_collect():
    assert not is_test_command("py -m pytest --version 2>&1")
    assert not is_test_command("pytest --help")
    assert not is_test_command("python -m pytest --collect-only -q")
    # 同一串命令里既有查版本又有真跑，仍算验证
    assert is_test_command("py -m pytest --version; python -m pytest -q")


def test_is_test_command_ignores_lookup_with_flags():
    # 真实日志里的假阳性：pytest 只是 Get-Command 的参数
    assert not is_test_command(
        "Get-Command python,python3,py,pytest -ErrorAction SilentlyContinue "
        "| Select-Object Name,Source"
    )


def test_is_pwsh_write():
    assert is_pwsh_write("Set-Content -Path a.py -Value 'x'")
    assert is_pwsh_write("'x' | Out-File a.py")
    assert is_pwsh_write("echo hi > a.py")
    assert not is_pwsh_write(
        "uv run --no-project --with pytest python -m pytest -q 2>&1"
    )
    assert not is_pwsh_write("Get-ChildItem -Recurse -File | Select-Object FullName")


def test_map_pwsh_write_as_write_file():
    step = _map("pwsh", {"command": "Set-Content -Path src/a.py -Value 'x'"}, "done")
    assert step["tool"] == "write_file"
    assert step["ok"] is True
    assert step["test_state"] is None


def test_map_pwsh_pytest_failure_is_signal_not_error():
    text = "FAILED tests/test_a.py::test_x - AssertionError\n1 failed, 2 passed\n[exit code: 1]"
    step = _map("pwsh", {"command": "python -m pytest -q"}, text)
    assert step["tool"] == "run_tests"
    assert step["ok"] is True
    assert step["test_state"] == ["test_x"]


def test_map_read_error():
    step = _map("read", {"file_path": "missing.py"}, "Error: not found", is_error=True)
    assert step["tool"] == "read_file"
    assert step["ok"] is False


def test_map_pwsh_exit_code_default_and_strict():
    text = "uv : error: Could not acquire lock\n[exit code: 1]"
    soft = _map("pwsh", {"command": "uv sync --all-packages"}, text)
    assert soft["tool"] == "bash"
    assert soft["ok"] is True
    assert soft["exit_code"] == 1

    strict = _map("pwsh", {"command": "uv sync --all-packages"}, text, strict_exit=True)
    assert strict["ok"] is False


def test_map_write_tool_as_write_file():
    step = _map("write", {"file_path": "hello.txt", "content": "hi\n"}, "created")
    assert step["tool"] == "write_file"
    assert step["args"]["content"] == "hi\n"


def test_map_edit_keeps_content_for_dedupe():
    step = _map(
        "edit",
        {"file_path": "a.py", "old_string": "x", "new_string": "y"},
        "updated",
    )
    assert step["tool"] == "write_file"
    assert step["args"]["content"] == "y"


def test_map_history_reads_results_by_call_id():
    rows = [
        {"ts": 1, "session": "s1", "event": _call("read", {"file_path": "a.py"}, "c1")},
        {"ts": 2, "session": "s1", "event": _result("1: x", "c1")},
        {"ts": 3, "session": "s1", "event": _call("read", {"file_path": "b.py"}, "c2")},
        {"ts": 4, "session": "s1", "event": _result("1: y", "c2")},
    ]
    session, history = map_history(rows)
    assert session == "s1"
    assert [step["step"] for step in history] == [1, 2]
    assert [step["tool"] for step in history] == ["read_file", "read_file"]
