from app import run


def test_total():
    assert run()["total"] == 18


def test_average():
    assert run()["average"] == 4.5


def test_middle():
    assert run()["middle"] == 4.0
