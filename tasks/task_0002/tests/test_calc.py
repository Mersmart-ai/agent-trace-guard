import pytest

from calc import average, sum_list


def test_sum_list():
    assert sum_list([1, 2, 3]) == 6


def test_average_three():
    assert average([1, 2, 10]) == pytest.approx(4.3333, rel=1e-3)


def test_average_two():
    assert average([2, 4]) == 3
