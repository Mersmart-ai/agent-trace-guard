from get_factors import get_factors


def test_get_factors_1():
    assert get_factors(*[1]) == []


def test_get_factors_2():
    assert get_factors(*[100]) == [2, 2, 5, 5]


def test_get_factors_3():
    assert get_factors(*[101]) == [101]


def test_get_factors_4():
    assert get_factors(*[104]) == [2, 2, 2, 13]


def test_get_factors_5():
    assert get_factors(*[2]) == [2]


def test_get_factors_6():
    assert get_factors(*[3]) == [3]


def test_get_factors_7():
    assert get_factors(*[17]) == [17]


def test_get_factors_8():
    assert get_factors(*[63]) == [3, 3, 7]


def test_get_factors_9():
    assert get_factors(*[74]) == [2, 37]


def test_get_factors_10():
    assert get_factors(*[73]) == [73]


def test_get_factors_11():
    assert get_factors(*[9837]) == [3, 3, 1093]

