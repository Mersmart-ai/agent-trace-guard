from flatten import flatten


def test_flatten_1():
    assert list(flatten(*[[[1, [], [2, 3]], [[4]], 5]])) == [1, 2, 3, 4, 5]


def test_flatten_2():
    assert list(flatten(*[[[], [], [], [], []]])) == []


def test_flatten_3():
    assert list(flatten(*[[[], [], 1, [], 1, [], []]])) == [1, 1]


def test_flatten_4():
    assert list(flatten(*[[1, 2, 3, [[4]]]])) == [1, 2, 3, 4]


def test_flatten_5():
    assert list(flatten(*[[1, 4, 6]])) == [1, 4, 6]


def test_flatten_6():
    assert list(flatten(*[['moe', 'curly', 'larry']])) == ['moe', 'curly', 'larry']


def test_flatten_7():
    assert list(flatten(*[['a', 'b', ['c'], ['d'], [['e']]]])) == ['a', 'b', 'c', 'd', 'e']

