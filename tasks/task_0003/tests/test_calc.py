import pytest

from calc import mean


def test_mean_normal():
    assert mean([2, 4, 6]) == 4


def test_mean_single():
    assert mean([7]) == 7


def test_mean_empty():
    assert mean([]) == 0
