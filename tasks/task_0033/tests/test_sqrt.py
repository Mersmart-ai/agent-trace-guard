import pytest

from sqrt import sqrt


def test_1():
    assert sqrt(*[2, 0.01]) == pytest.approx(1.4166666666666665, abs=0.01)


def test_2():
    assert sqrt(*[2, 0.5]) == pytest.approx(1.5, abs=0.5)


def test_3():
    assert sqrt(*[2, 0.3]) == pytest.approx(1.5, abs=0.3)


def test_4():
    assert sqrt(*[4, 0.2]) == pytest.approx(2, abs=0.2)


def test_5():
    assert sqrt(*[27, 0.01]) == pytest.approx(5.196164639727311, abs=0.01)


def test_6():
    assert sqrt(*[33, 0.05]) == pytest.approx(5.744627526262464, abs=0.05)


def test_7():
    assert sqrt(*[170, 0.03]) == pytest.approx(13.038404876679632, abs=0.03)

