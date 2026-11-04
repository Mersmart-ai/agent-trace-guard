from powerset import powerset


def test_1():
    assert powerset(*[['a', 'b', 'c']]) == [[], ['c'], ['b'], ['b', 'c'], ['a'], ['a', 'c'], ['a', 'b'], ['a', 'b', 'c']]


def test_2():
    assert powerset(*[['a', 'b']]) == [[], ['b'], ['a'], ['a', 'b']]


def test_3():
    assert powerset(*[['a']]) == [[], ['a']]


def test_4():
    assert powerset(*[[]]) == [[]]


def test_5():
    assert powerset(*[['x', 'df', 'z', 'm']]) == [[], ['m'], ['z'], ['z', 'm'], ['df'], ['df', 'm'], ['df', 'z'], ['df', 'z', 'm'], ['x'], ['x', 'm'], ['x', 'z'], ['x', 'z', 'm'], ['x', 'df'], ['x', 'df', 'm'], ['x', 'df', 'z'], ['x', 'df', 'z', 'm']]

