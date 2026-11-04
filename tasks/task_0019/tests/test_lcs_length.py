from lcs_length import lcs_length


def test_1():
    assert lcs_length(*['witch', 'sandwich']) == 2


def test_2():
    assert lcs_length(*['meow', 'homeowner']) == 4


def test_3():
    assert lcs_length(*['fun', '']) == 0


def test_4():
    assert lcs_length(*['fun', 'function']) == 3


def test_5():
    assert lcs_length(*['cyborg', 'cyber']) == 3


def test_6():
    assert lcs_length(*['physics', 'physics']) == 7


def test_7():
    assert lcs_length(*['space age', 'pace a']) == 6


def test_8():
    assert lcs_length(*['flippy', 'floppy']) == 3


def test_9():
    assert lcs_length(*['acbdegcedbg', 'begcfeubk']) == 3

