from bitcount import bitcount


def test_1():
    assert bitcount(*[127]) == 7


def test_2():
    assert bitcount(*[128]) == 1


def test_3():
    assert bitcount(*[3005]) == 9


def test_4():
    assert bitcount(*[13]) == 3


def test_5():
    assert bitcount(*[14]) == 3


def test_6():
    assert bitcount(*[27]) == 4


def test_7():
    assert bitcount(*[834]) == 4


def test_8():
    assert bitcount(*[254]) == 7


def test_9():
    assert bitcount(*[256]) == 1

