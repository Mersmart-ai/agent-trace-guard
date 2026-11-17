"""规则监控的测试：每条规则命中/不命中，以及在线前缀的 no_verify 语义。"""
import json
from pathlib import Path

from fbs.analysis.monitor import rule_alarms, strict_alarms

ARCHIVE = Path(__file__).resolve().parents[1] / "data" / "raw_v1" / "run_traces"


def _step(n, tool, args=None, ok=True, test_state=None, judge=None):
    return {
        "step": n,
        "tool": tool,
        "args": args or {},
        "result": {},
        "ok": ok,
        "test_state": test_state,
        "judge": judge,
    }


def test_clean_trace_no_alarms():
    trace = json.loads((ARCHIVE / "task_0001" / "r01.json").read_text(encoding="utf-8"))
    assert rule_alarms(trace["steps"]) == []


def test_no_verify_only_at_finish():
    history = [
        _step(1, "read_file", {"path": "a.py"}),
        _step(2, "finish"),
    ]
    names = [a["rule"] for a in rule_alarms(history, final=True)]
    assert "no_verify" in names

    # 在线前缀：最后一步不是 finish，不能因为“暂时没测”报警
    names = [a["rule"] for a in rule_alarms(history[:-1], final=False)]
    assert "no_verify" not in names

    names = [a["rule"] for a in rule_alarms(history, final=False)]
    assert "no_verify" in names


def test_delta():
    history = [
        _step(1, "read_file", {"path": "a.py"}),
        _step(2, "write_file", {"path": "a.py", "content": "x"}, test_state=[]),
        _step(3, "write_file", {"path": "a.py", "content": "y"}, test_state=["t"]),
    ]
    names = [a["rule"] for a in rule_alarms(history)]
    assert "delta" in names


def test_dup2():
    history = [
        _step(1, "read_file", {"path": "a.py"}),
        _step(2, "read_file", {"path": "a.py"}),
        _step(3, "read_file", {"path": "a.py"}),
    ]
    names = [a["rule"] for a in rule_alarms(history)]
    assert "dup2" in names


def test_error():
    history = [_step(1, "read_file", {"path": "missing.py"}, ok=False)]
    names = [a["rule"] for a in rule_alarms(history)]
    assert "error" in names


def test_long_gap():
    history = [
        _step(i, "read_file", {"path": f"f{i}.py"})
        for i in range(1, 17)
    ]
    names = [a["rule"] for a in rule_alarms(history)]
    assert "long_gap" in names


def test_unverified_write():
    history = [
        _step(1, "read_file", {"path": "a.py"}),
        _step(2, "write_file", {"path": "a.py", "content": "x"}, test_state=[]),
        _step(3, "run_tests", test_state=[]),
        _step(4, "write_file", {"path": "a.py", "content": "y"}, test_state=[]),
        _step(5, "finish"),
    ]
    names = [a["rule"] for a in rule_alarms(history)]
    assert "unverified_write" in names


def test_verified_write_no_alarm():
    history = [
        _step(1, "read_file", {"path": "a.py"}),
        _step(2, "write_file", {"path": "a.py", "content": "x"}, test_state=[]),
        _step(3, "run_tests", test_state=[]),
        _step(4, "finish"),
    ]
    names = [a["rule"] for a in rule_alarms(history)]
    assert "unverified_write" not in names


def test_blind_code_task():
    history = [
        _step(1, "write_file", {"path": "a.py", "content": "x"}, test_state=[]),
    ]
    names = [a["rule"] for a in rule_alarms(history)]
    assert "blind" in names


def test_blind_terminal_task_does_not_fire():
    history = [
        _step(1, "bash", {"command": "cat a.py"}, test_state=[]),
        _step(2, "bash", {"command": "echo x > a.py"}, test_state=[]),
    ]
    names = [a["rule"] for a in rule_alarms(history)]
    assert "blind" not in names


def test_strict_alarms_filters_blind():
    alarms = [{"rule": "blind", "step": 1}, {"rule": "delta", "step": 2}]
    assert [a["rule"] for a in strict_alarms(alarms)] == ["delta"]
