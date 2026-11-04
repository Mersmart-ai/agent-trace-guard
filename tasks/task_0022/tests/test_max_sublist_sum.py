from max_sublist_sum import max_sublist_sum


def test_1():
    assert max_sublist_sum(*[[4, -5, 2, 1, -1, 3]]) == 5


def test_2():
    assert max_sublist_sum(*[[0, -1, 2, -1, 3, -1, 0]]) == 4


def test_3():
    assert max_sublist_sum(*[[3, 4, 5]]) == 12


def test_4():
    assert max_sublist_sum(*[[4, -2, -8, 5, -2, 7, 7, 2, -6, 5]]) == 19


def test_5():
    assert max_sublist_sum(*[[-4, -4, -5]]) == 0


def test_6():
    assert max_sublist_sum(*[[-2, 1, -3, 4, -1, 2, 1, -5, 4]]) == 6

