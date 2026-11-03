from bitcount import bitcount


def test_bitcount_1():
    assert bitcount(*[127]) == 7


def test_bitcount_2():
    assert bitcount(*[128]) == 1


def test_bitcount_3():
    assert bitcount(*[3005]) == 9


def test_bitcount_4():
    assert bitcount(*[13]) == 3


def test_bitcount_5():
    assert bitcount(*[14]) == 3


def test_bitcount_6():
    assert bitcount(*[27]) == 4


def test_bitcount_7():
    assert bitcount(*[834]) == 4


def test_bitcount_8():
    assert bitcount(*[254]) == 7


def test_bitcount_9():
    assert bitcount(*[256]) == 1

