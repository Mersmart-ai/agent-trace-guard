from sieve import sieve


def test_1():
    assert sieve(*[1]) == []


def test_2():
    assert sieve(*[2]) == [2]


def test_3():
    assert sieve(*[4]) == [2, 3]


def test_4():
    assert sieve(*[7]) == [2, 3, 5, 7]


def test_5():
    assert sieve(*[20]) == [2, 3, 5, 7, 11, 13, 17, 19]


def test_6():
    assert sieve(*[50]) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]

