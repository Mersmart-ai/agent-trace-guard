"""locate 的测试。全部用硬编码数据，不碰 API、不跑真实任务。"""
import pytest

from fbs.locate import build_states, locate, render


# ---------- build_states ----------

def test_build_states():
    history = [
        {"step": 1, "test_state": None},
        {"step": 2, "test_state": []},
        {"step": 3, "test_state": ["a"]},
    ]
    assert build_states(history) == [None, [], ["a"]]


def test_build_states_length_equals_steps():
    """列表长度必须等于步数，否则下标对不上步号。"""
    history = [{"step": i, "test_state": None} for i in range(1, 8)]
    assert len(build_states(history)) == 7


# ---------- render ----------

def test_render():
    assert render([None, None, ["a"], [], [], None]) == "..FPP."


# ---------- locate：三种顶层返回 ----------

def test_never_tested_returns_none():
    """一次都没测过 → None（"未验证就提交"）"""
    assert locate([None, None, None]) is None
    assert locate([]) is None


def test_all_pass_returns_empty_dict():
    """最终全过 → {}（没有要归因的）"""
    assert locate([[], []]) == {}


def test_broken_then_fixed_returns_empty():
    """中间坏过，但最后修好了 → 还是 {}"""
    assert locate([[], ["a"], []]) == {}


# ---------- locate：归因到步号 ----------

def test_caught_at_second_step():
    assert locate([[], ["a"]]) == {"a": 2}


def test_two_tests_broken_at_different_steps():
    """a 在第 2 步坏，b 在第 3 步坏"""
    assert locate([[], ["a"], ["a", "b"]]) == {"a": 2, "b": 3}


def test_last_entry_wins():
    """a 坏过、修好、又坏 → 记最后一次"""
    assert locate([["a"], [], ["a"]]) == {"a": 3}


def test_fixed_test_not_reported():
    """b 坏过又修好了，最终状态里没有它，就不该出现在结果里"""
    assert locate([[], ["a", "b"], ["a"]]) == {"a": 2}


# ---------- locate：基线就坏（记 0）----------

def test_baseline_broken_is_zero():
    """第一次测就已经红了 → 0，不是第 1 步"""
    assert locate([["a"], ["a"]]) == {"a": 0}


def test_mixed_baseline_and_caught():
    """a 本来就没过（0）；b 是第 2 步弄坏的"""
    assert locate([["a"], ["a", "b"]]) == {"a": 0, "b": 2}


# ---------- 串起来：task_0006 的真实形状 ----------

def test_real_shape_task0006_passed():
    """写两处，第一处还红、第二处绿了，最后又测一次 —— 最终全过"""
    history = [
        {"step": 1, "test_state": None},
        {"step": 2, "test_state": None},
        {"step": 3, "test_state": None},
        {"step": 4, "test_state": None},
        {"step": 5, "test_state": ["test_average"]},
        {"step": 6, "test_state": []},
        {"step": 7, "test_state": []},
        {"step": 8, "test_state": None},
    ]
    states = build_states(history)
    assert render(states) == "....FPP."
    assert locate(states) == {}


def test_real_shape_regression():
    """模型没修好原来的 bug，还把本来绿的 test_total 弄坏了。

    test_average: 第一次测（第5步）就红 → 0（基线）
    test_total:   第5步不在、第6步在 → 6
    """
    history = [
        {"step": 1, "test_state": None},
        {"step": 2, "test_state": None},
        {"step": 3, "test_state": None},
        {"step": 4, "test_state": None},
        {"step": 5, "test_state": ["test_average"]},
        {"step": 6, "test_state": ["test_average", "test_total"]},
        {"step": 7, "test_state": ["test_average", "test_total"]},
        {"step": 8, "test_state": None},
    ]
    states = build_states(history)
    assert render(states) == "....FFF."
    assert locate(states) == {"test_average": 0, "test_total": 6}
