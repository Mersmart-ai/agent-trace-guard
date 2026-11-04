import pytest

from calc import mean


def test_normal():
    assert mean([2, 4, 6]) == 4


def test_single():
    assert mean([7]) == 7


def test_zero():
    assert mean([0]) == 0


def test_float():
    assert mean([1.5, 2.5]) == pytest.approx(2.0)


def test_tuple():
    assert mean((2, 4)) == 3


def test_empty():
    assert mean([]) == 0
