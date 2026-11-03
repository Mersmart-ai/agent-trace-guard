from hanoi import hanoi


def test_hanoi_1():
    assert hanoi(*[0, 1, 3]) == [tuple(x) for x in []]


def test_hanoi_2():
    assert hanoi(*[1, 1, 3]) == [tuple(x) for x in [[1, 3]]]


def test_hanoi_3():
    assert hanoi(*[2, 1, 3]) == [tuple(x) for x in [[1, 2], [1, 3], [2, 3]]]


def test_hanoi_4():
    assert hanoi(*[3, 1, 3]) == [tuple(x) for x in [[1, 3], [1, 2], [3, 2], [1, 3], [2, 1], [2, 3], [1, 3]]]


def test_hanoi_5():
    assert hanoi(*[4, 1, 3]) == [tuple(x) for x in [[1, 2], [1, 3], [2, 3], [1, 2], [3, 1], [3, 2], [1, 2], [1, 3], [2, 3], [2, 1], [3, 1], [2, 3], [1, 2], [1, 3], [2, 3]]]


def test_hanoi_6():
    assert hanoi(*[2, 1, 2]) == [tuple(x) for x in [[1, 3], [1, 2], [3, 2]]]


def test_hanoi_7():
    assert hanoi(*[2, 1, 1]) == [tuple(x) for x in [[1, 2], [1, 1], [2, 1]]]


def test_hanoi_8():
    assert hanoi(*[2, 3, 1]) == [tuple(x) for x in [[3, 2], [3, 1], [2, 1]]]

