from find_first_in_sorted import find_first_in_sorted


def test_find_first_in_sorted_1():
    assert find_first_in_sorted(*[[3, 4, 5, 5, 5, 5, 6], 5]) == 2


def test_find_first_in_sorted_2():
    assert find_first_in_sorted(*[[3, 4, 5, 5, 5, 5, 6], 7]) == -1


def test_find_first_in_sorted_3():
    assert find_first_in_sorted(*[[3, 4, 5, 5, 5, 5, 6], 2]) == -1


def test_find_first_in_sorted_4():
    assert find_first_in_sorted(*[[3, 6, 7, 9, 9, 10, 14, 27], 14]) == 6


def test_find_first_in_sorted_5():
    assert find_first_in_sorted(*[[0, 1, 6, 8, 13, 14, 67, 128], 80]) == -1


def test_find_first_in_sorted_6():
    assert find_first_in_sorted(*[[0, 1, 6, 8, 13, 14, 67, 128], 67]) == 6


def test_find_first_in_sorted_7():
    assert find_first_in_sorted(*[[0, 1, 6, 8, 13, 14, 67, 128], 128]) == 7

