import pytest

from app import run


def test_total():
    assert run()["total"] == 15


def test_average():
    assert run()["average"] == pytest.approx(5.0)
