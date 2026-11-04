from app import run


def test_case_1():
    assert run()["total"] == 18


def test_average():
    assert run()["average"] == 4.5


def test_middle():
    assert run()["middle"] == 4.0
