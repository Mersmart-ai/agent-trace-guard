from longest_common_subsequence import longest_common_subsequence


def test_1():
    assert longest_common_subsequence(*['headache', 'pentadactyl']) == 'eadac'


def test_2():
    assert longest_common_subsequence(*['daenarys', 'targaryen']) == 'aary'


def test_3():
    assert longest_common_subsequence(*['XMJYAUZ', 'MZJAWXU']) == 'MJAU'


def test_4():
    assert longest_common_subsequence(*['thisisatest', 'testing123testing']) == 'tsitest'


def test_5():
    assert longest_common_subsequence(*['1234', '1224533324']) == '1234'


def test_6():
    assert longest_common_subsequence(*['abcbdab', 'bdcaba']) == 'bcba'


def test_7():
    assert longest_common_subsequence(*['TATAGC', 'TAGCAG']) == 'TAAG'


def test_8():
    assert longest_common_subsequence(*['ABCBDAB', 'BDCABA']) == 'BCBA'


def test_9():
    assert longest_common_subsequence(*['ABCD', 'XBCYDQ']) == 'BCD'


def test_10():
    assert longest_common_subsequence(*['acbdegcedbg', 'begcfeubk']) == 'begceb'

