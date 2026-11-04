from flatten import flatten


def test_1():
    assert list(flatten(*[[[1, [], [2, 3]], [[4]], 5]])) == [1, 2, 3, 4, 5]


def test_2():
    assert list(flatten(*[[[], [], [], [], []]])) == []


def test_3():
    assert list(flatten(*[[[], [], 1, [], 1, [], []]])) == [1, 1]


def test_4():
    assert list(flatten(*[[1, 2, 3, [[4]]]])) == [1, 2, 3, 4]


def test_5():
    assert list(flatten(*[[1, 4, 6]])) == [1, 4, 6]


def test_6():
    assert list(flatten(*[['moe', 'curly', 'larry']])) == ['moe', 'curly', 'larry']


def test_7():
    assert list(flatten(*[['a', 'b', ['c'], ['d'], [['e']]]])) == ['a', 'b', 'c', 'd', 'e']

