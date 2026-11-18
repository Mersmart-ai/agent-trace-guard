"""模型可见的 history 必须剥掉 harness 内部字段。"""
from fbs.agent.policy import visible_history


def test_visible_history_strips_test_state_and_judge():
    history = [
        {"step": 1, "tool": "write_file", "ok": True,
         "test_state": [], "judge": "fast", "result": "写入成功"},
    ]
    visible = visible_history(history)
    assert visible == [
        {"step": 1, "tool": "write_file", "ok": True, "result": "写入成功"}
    ]
    # 原对象不能被改
    assert history[0]["test_state"] == []
    assert history[0]["judge"] == "fast"


def test_visible_history_keeps_normal_fields():
    history = [{"step": 1, "tool": "read_file", "ok": True, "result": "x"}]
    assert visible_history(history) == history
