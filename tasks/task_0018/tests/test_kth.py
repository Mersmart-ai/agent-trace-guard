from kth import kth


def test_1():
    assert kth(*[[1, 2, 3, 4, 5, 6, 7], 4]) == 5


def test_2():
    assert kth(*[[3, 6, 7, 1, 6, 3, 8, 9], 5]) == 7


def test_3():
    assert kth(*[[3, 6, 7, 1, 6, 3, 8, 9], 2]) == 3


def test_4():
    assert kth(*[[2, 6, 8, 3, 5, 7], 0]) == 2


def test_5():
    assert kth(*[[34, 25, 7, 1, 9], 4]) == 34


def test_6():
    assert kth(*[[45, 2, 6, 8, 42, 90, 322], 1]) == 6


def test_7():
    assert kth(*[[45, 2, 6, 8, 42, 90, 322], 6]) == 322

