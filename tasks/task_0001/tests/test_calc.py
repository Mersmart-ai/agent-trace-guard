import pytest

from calc import add, mean, multiply


def test_add_positive():
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-1, -2) == -3


def test_add_zero():
    # 干扰项：add 写成 a - b 时，0 - 0 也等于 0，这条照样是绿的
    assert add(0, 0) == 0


def test_add_float():
    assert add(1.5, 2.5) == pytest.approx(4.0)


def test_multiply():
    assert multiply(2, 3) == 6


def test_mean():
    assert mean([1, 2, 3, 4]) == pytest.approx(2.5)
