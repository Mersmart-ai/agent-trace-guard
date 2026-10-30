from app import run


def test_total():
    assert run()["total"] == 15


def test_average():
    assert run()["average"] == 5.0
