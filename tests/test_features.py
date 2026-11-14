"""特征提取的测试：硬编码 trace + 一条真实归档 trace。"""
import json
from pathlib import Path

from fbs.analysis.features import duplicate_rate, run_features, step_features
from fbs.data.audit import classify_run

ARCHIVE = Path(__file__).resolve().parents[1] / "data" / "raw_v1" / "run_traces"


def _trace():
    return {
        "steps": [
            {"tool": "list_files"},
            {"tool": "grep"},
            {"tool": "read_file"},
            # 只读 bash 算 read
            {"tool": "bash", "args": {"command": "cat a.py"}},
            # 重定向算 write
            {"tool": "bash", "args": {"command": "echo x > a.py"}},
            {"tool": "run_tests"},
            {"tool": "finish"},
        ]
    }


def test_run_features_uses_tool_kind():
    assert run_features(_trace()) == {
        "steps": 7,
        "navigate": 2,
        "read": 2,
        "write": 1,
        "verify": 1,
        "other": 1,
    }


def test_run_features_empty_trace():
    assert run_features({}) == {
        "steps": 0,
        "navigate": 0,
        "read": 0,
        "write": 0,
        "verify": 0,
        "other": 0,
    }


def test_features_match_audit_counts():
    """同一份 history，features 和 audit 的计数必须一致。"""
    trace = _trace()
    f = run_features(trace)
    row = classify_run(trace)
    for kind in ("navigate", "read", "write", "verify", "other"):
        assert f[kind] == row[kind]


def test_run_features_on_real_clean_trace():
    path = ARCHIVE / "task_0001" / "r01.json"
    trace = json.loads(path.read_text(encoding="utf-8"))
    assert run_features(trace) == {
        "steps": 5,
        "navigate": 1,
        "read": 1,
        "write": 1,
        "verify": 1,
        "other": 1,
    }


def _step_trace():
    return {
        "steps": [
            {"step": 1, "tool": "read_file", "ok": True, "test_state": None},
            {"step": 2, "tool": "write_file", "ok": True,
             "test_state": ["a"], "judge": "j1"},
            {"step": 3, "tool": "run_tests", "ok": True,
             "test_state": ["a"], "judge": "j1"},
            {"step": 4, "tool": "write_file", "ok": False,
             "test_state": [], "judge": "j1"},
            {"step": 5, "tool": "finish", "ok": True, "test_state": None},
        ]
    }


def test_step_features_tracks_state_and_gaps():
    rows = step_features(_step_trace())
    assert rows == [
        {"step": 1, "tool": "read_file", "kind": "read", "ok": True,
         "tested": False, "fails": 0, "delta_fails": 0,
         "since_test": 1, "since_write": 1, "result_len": 0,
         "is_dup": False, "repeat_streak": 0, "prev_kind": None},
        {"step": 2, "tool": "write_file", "kind": "write", "ok": True,
         "tested": True, "fails": 1, "delta_fails": 0,
         "since_test": 2, "since_write": 0, "result_len": 0,
         "is_dup": False, "repeat_streak": 0, "prev_kind": "read"},
        {"step": 3, "tool": "run_tests", "kind": "verify", "ok": True,
         "tested": True, "fails": 1, "delta_fails": 0,
         "since_test": 0, "since_write": 1, "result_len": 0,
         "is_dup": False, "repeat_streak": 0, "prev_kind": "write"},
        # 和第 2 步同一个动作（write_file + 空 args），但不是连续重复
        {"step": 4, "tool": "write_file", "kind": "write", "ok": False,
         "tested": True, "fails": 0, "delta_fails": -1,
         "since_test": 1, "since_write": 0, "result_len": 0,
         "is_dup": True, "repeat_streak": 0, "prev_kind": "verify"},
        {"step": 5, "tool": "finish", "kind": "other", "ok": True,
         "tested": False, "fails": 0, "delta_fails": 0,
         "since_test": 2, "since_write": 1, "result_len": 0,
         "is_dup": False, "repeat_streak": 0, "prev_kind": "write"},
    ]


def test_step_features_resets_delta_on_judge_change():
    """判据换了，失败条数不能直接相减。"""
    trace = {"steps": [
        {"step": 1, "tool": "run_tests", "ok": True,
         "test_state": ["a", "b"], "judge": "j1"},
        {"step": 2, "tool": "run_tests", "ok": True,
         "test_state": ["c"], "judge": "j2"},
    ]}
    rows = step_features(trace)
    assert rows[1]["delta_fails"] == 0


def test_step_features_on_real_clean_trace():
    path = ARCHIVE / "task_0001" / "r01.json"
    trace = json.loads(path.read_text(encoding="utf-8"))
    rows = step_features(trace)
    assert [
        (r["kind"], r["tested"], r["fails"], r["since_test"], r["since_write"])
        for r in rows
    ] == [
        ("navigate", False, 0, 1, 1),
        ("read", False, 0, 2, 2),
        # 写后强制判分：tested=True，但不是 run_tests，since_test 不归零
        ("write", True, 0, 3, 0),
        ("verify", True, 0, 0, 1),
        ("other", False, 0, 1, 2),
    ]


def test_step_features_marks_consecutive_duplicates():
    trace = {"steps": [
        {"tool": "read_file", "args": {"path": "a"}},
        {"tool": "read_file", "args": {"path": "a"}},
        {"tool": "read_file", "args": {"path": "a"}},
        {"tool": "read_file", "args": {"path": "b"}},
    ]}
    rows = step_features(trace)
    assert [r["is_dup"] for r in rows] == [False, True, True, False]
    assert [r["repeat_streak"] for r in rows] == [0, 1, 2, 0]


def test_duplicate_rate():
    assert duplicate_rate([]) == 0.0
    steps = [
        {"tool": "read_file", "args": {"path": "a"}},
        {"tool": "read_file", "args": {"path": "a"}},
        {"tool": "read_file", "args": {"path": "b"}},
    ]
    assert duplicate_rate(steps) == 0.333
