from pascal import pascal


def test_1():
    assert pascal(*[1]) == [[1]]


def test_2():
    assert pascal(*[2]) == [[1], [1, 1]]


def test_3():
    assert pascal(*[3]) == [[1], [1, 1], [1, 2, 1]]


def test_4():
    assert pascal(*[4]) == [[1], [1, 1], [1, 2, 1], [1, 3, 3, 1]]


def test_5():
    assert pascal(*[5]) == [[1], [1, 1], [1, 2, 1], [1, 3, 3, 1], [1, 4, 6, 4, 1]]

