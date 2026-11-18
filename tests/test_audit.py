"""审计的最终判分：优先 final_test_state，旧 trace 退回 locate(steps)。"""
from fbs.data.audit import classify_run


def _trace(final="__missing__", last_state=None):
    steps = [
        {"step": 1, "tool": "read_file", "ok": True, "test_state": None},
        {"step": 2, "tool": "write_file", "ok": True,
         "args": {"path": "a.py", "content": "x"},
         "result": "写入成功", "test_state": last_state},
        {"step": 3, "tool": "finish", "ok": True, "test_state": None},
    ]
    data = {"task": "t", "run_id": "t_r01", "reason": "right exit", "steps": steps}
    if final != "__missing__":
        data["final_test_state"] = final
    return data


def test_classify_run_prefers_final_test_state():
    # steps 里最后一次快速判据是红的，完整判据是绿的 -> 以完整判据为准
    row = classify_run(_trace(final=[], last_state=["fast_red"]))
    assert row["final_test_state"] == "[]"
    assert row["healthy_class"] == "clean_success"


def test_classify_run_parses_json_string_final():
    row = classify_run(_trace(final="[]", last_state=["fast_red"]))
    assert row["final_test_state"] == "[]"
    assert row["healthy_class"] == "clean_success"


def test_classify_run_falls_back_to_steps():
    row = classify_run(_trace(last_state=["a"]))
    assert row["final_test_state"] == '["a"]'
    assert row["healthy_class"] == "task_failure"
