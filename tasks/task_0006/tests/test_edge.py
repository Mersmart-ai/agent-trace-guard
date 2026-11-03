from app import run


def test_report_keys():
    assert set(run().keys()) == {"total", "average"}


def test_average_is_float():
    assert isinstance(run()["average"], float)
