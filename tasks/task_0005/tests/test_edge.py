from app import run


def test_report_keys():
    assert set(run().keys()) == {"total", "average"}


def test_average_is_float():
    assert isinstance(run()["average"], float)


def test_idempotent():
    # 调两次结果必须一样，防止有隐藏的状态被改坏
    assert run() == run()
