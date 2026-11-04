from kheapsort import kheapsort


def test_1():
    assert list(kheapsort(*[[1, 2, 3, 4, 5], 0])) == [1, 2, 3, 4, 5]


def test_2():
    assert list(kheapsort(*[[3, 2, 1, 5, 4], 2])) == [1, 2, 3, 4, 5]


def test_3():
    assert list(kheapsort(*[[5, 4, 3, 2, 1], 4])) == [1, 2, 3, 4, 5]


def test_4():
    assert list(kheapsort(*[[3, 12, 5, 1, 6], 3])) == [1, 3, 5, 6, 12]

