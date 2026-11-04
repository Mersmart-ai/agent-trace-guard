import pytest

from calc import average, sum_list


def test_case_1():
    assert sum_list([1, 2, 3]) == 6


def test_three():
    assert average([1, 2, 10]) == pytest.approx(4.3333, rel=1e-3)


def test_two():
    # 干扰项：只有两个数时，「最大 + 最小 除以 2」恰好等于平均值
    assert average([2, 4]) == 3


def test_single():
    # 干扰项：单个数时也相等
    assert average([7]) == 7


def test_wide():
    # 差距拉开才会暴露
    assert average([1, 2, 100]) == pytest.approx(34.3333, rel=1e-3)
