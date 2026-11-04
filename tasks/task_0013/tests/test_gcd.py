from gcd import gcd


def test_1():
    assert gcd(*[17, 0]) == 17


def test_2():
    assert gcd(*[13, 13]) == 13


def test_3():
    assert gcd(*[37, 600]) == 1


def test_4():
    assert gcd(*[20, 100]) == 20


def test_5():
    assert gcd(*[624129, 2061517]) == 18913


def test_6():
    assert gcd(*[3, 12]) == 3

