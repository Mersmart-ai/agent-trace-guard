import pytest

from app import run


def test_case_1():
    assert run()["total"] == 15


def test_average():
    assert run()["average"] == pytest.approx(5.0)


def test_report_keys():
    assert set(run().keys()) == {"total", "average"}


def test_average_is_float():
    assert isinstance(run()["average"], float)
