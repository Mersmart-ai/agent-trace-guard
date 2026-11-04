"""校准任务：两条断言互相矛盾，任何函数都不可能同时满足。

这不是评测样本，是用来验证「失败路径」管道的。就像新买的仪器先用已知
样本校一遍，确认读数正常，再拿去测病人。

两个 type(r) is int 是为了堵住"返回一个能同时等于 4 和 5 的自定义对象"
这种取巧写法——那不算解题，算作弊，会污染校准结果。
"""
from calc import f


def test_wants_4():
    r = f(3)
    assert type(r) is int
    assert r == 4


def test_wants_5():
    r = f(3)
    assert type(r) is int
    assert r == 5
