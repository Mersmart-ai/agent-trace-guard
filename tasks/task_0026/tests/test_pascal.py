from pascal import pascal


def test_pascal_1():
    assert pascal(*[1]) == [[1]]


def test_pascal_2():
    assert pascal(*[2]) == [[1], [1, 1]]


def test_pascal_3():
    assert pascal(*[3]) == [[1], [1, 1], [1, 2, 1]]


def test_pascal_4():
    assert pascal(*[4]) == [[1], [1, 1], [1, 2, 1], [1, 3, 3, 1]]


def test_pascal_5():
    assert pascal(*[5]) == [[1], [1, 1], [1, 2, 1], [1, 3, 3, 1], [1, 4, 6, 4, 1]]

