from shunting_yard import shunting_yard


def test_shunting_yard_1():
    assert shunting_yard(*[[]]) == []


def test_shunting_yard_2():
    assert shunting_yard(*[[30]]) == [30]


def test_shunting_yard_3():
    assert shunting_yard(*[[10, '-', 5, '-', 2]]) == [10, 5, '-', 2, '-']


def test_shunting_yard_4():
    assert shunting_yard(*[[34, '-', 12, '/', 5]]) == [34, 12, 5, '/', '-']


def test_shunting_yard_5():
    assert shunting_yard(*[[4, '+', 9, '*', 9, '-', 10, '+', 13]]) == [4, 9, 9, '*', '+', 10, '-', 13, '+']


def test_shunting_yard_6():
    assert shunting_yard(*[[7, '*', 43, '-', 7, '+', 13, '/', 7]]) == [7, 43, '*', 7, '-', 13, 7, '/', '+']

