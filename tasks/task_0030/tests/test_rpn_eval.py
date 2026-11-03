from rpn_eval import rpn_eval


def test_rpn_eval_1():
    assert rpn_eval(*[[3.0, 5.0, '+', 2.0, '/']]) == 4.0


def test_rpn_eval_2():
    assert rpn_eval(*[[2.0, 2.0, '+']]) == 4.0


def test_rpn_eval_3():
    assert rpn_eval(*[[7.0, 4.0, '+', 3.0, '-']]) == 8.0


def test_rpn_eval_4():
    assert rpn_eval(*[[1.0, 2.0, '*', 3.0, 4.0, '*', '+']]) == 14.0


def test_rpn_eval_5():
    assert rpn_eval(*[[5.0, 9.0, 2.0, '*', '+']]) == 23.0


def test_rpn_eval_6():
    assert rpn_eval(*[[5.0, 1.0, 2.0, '+', 4.0, '*', '+', 3.0, '-']]) == 14.0

