from lcs_length import lcs_length


def test_lcs_length_1():
    assert lcs_length(*['witch', 'sandwich']) == 2


def test_lcs_length_2():
    assert lcs_length(*['meow', 'homeowner']) == 4


def test_lcs_length_3():
    assert lcs_length(*['fun', '']) == 0


def test_lcs_length_4():
    assert lcs_length(*['fun', 'function']) == 3


def test_lcs_length_5():
    assert lcs_length(*['cyborg', 'cyber']) == 3


def test_lcs_length_6():
    assert lcs_length(*['physics', 'physics']) == 7


def test_lcs_length_7():
    assert lcs_length(*['space age', 'pace a']) == 6


def test_lcs_length_8():
    assert lcs_length(*['flippy', 'floppy']) == 3


def test_lcs_length_9():
    assert lcs_length(*['acbdegcedbg', 'begcfeubk']) == 3

