from to_base import to_base


def test_1():
    assert to_base(*[8227, 18]) == '1771'


def test_2():
    assert to_base(*[73, 8]) == '111'


def test_3():
    assert to_base(*[16, 19]) == 'G'


def test_4():
    assert to_base(*[31, 16]) == '1F'


def test_5():
    assert to_base(*[41, 2]) == '101001'


def test_6():
    assert to_base(*[44, 5]) == '134'


def test_7():
    assert to_base(*[27, 23]) == '14'


def test_8():
    assert to_base(*[56, 23]) == '2A'


def test_9():
    assert to_base(*[8237, 24]) == 'E75'


def test_10():
    assert to_base(*[8237, 34]) == '749'

