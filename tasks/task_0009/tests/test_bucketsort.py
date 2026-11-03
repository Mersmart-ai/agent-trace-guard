from bucketsort import bucketsort


def test_bucketsort_1():
    assert bucketsort(*[[], 14]) == []


def test_bucketsort_2():
    assert bucketsort(*[[3, 11, 2, 9, 1, 5], 12]) == [1, 2, 3, 5, 9, 11]


def test_bucketsort_3():
    assert bucketsort(*[[3, 2, 4, 2, 3, 5], 6]) == [2, 2, 3, 3, 4, 5]


def test_bucketsort_4():
    assert bucketsort(*[[1, 3, 4, 6, 4, 2, 9, 1, 2, 9], 10]) == [1, 1, 2, 2, 3, 4, 4, 6, 9, 9]


def test_bucketsort_5():
    assert bucketsort(*[[20, 19, 18, 17, 16, 15, 14, 13, 12, 11], 21]) == [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]


def test_bucketsort_6():
    assert bucketsort(*[[20, 21, 22, 23, 24, 25, 26, 27, 28, 29], 30]) == [20, 21, 22, 23, 24, 25, 26, 27, 28, 29]


def test_bucketsort_7():
    assert bucketsort(*[[8, 5, 3, 1, 9, 6, 0, 7, 4, 2, 5], 10]) == [0, 1, 2, 3, 4, 5, 5, 6, 7, 8, 9]

