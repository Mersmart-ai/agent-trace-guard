from possible_change import possible_change


def test_possible_change_1():
    assert possible_change(*[[1, 4, 2], -7]) == 0


def test_possible_change_2():
    assert possible_change(*[[1, 5, 10, 25], 11]) == 4


def test_possible_change_3():
    assert possible_change(*[[1, 5, 10, 25], 75]) == 121


def test_possible_change_4():
    assert possible_change(*[[1, 5, 10, 25], 34]) == 18


def test_possible_change_5():
    assert possible_change(*[[1, 5, 10], 34]) == 16


def test_possible_change_6():
    assert possible_change(*[[1, 5, 10, 25], 140]) == 568


def test_possible_change_7():
    assert possible_change(*[[1, 5, 10, 25, 50], 140]) == 786


def test_possible_change_8():
    assert possible_change(*[[1, 5, 10, 25, 50, 100], 140]) == 817


def test_possible_change_9():
    assert possible_change(*[[1, 3, 7, 42, 78], 140]) == 981


def test_possible_change_10():
    assert possible_change(*[[3, 7, 42, 78], 140]) == 20

