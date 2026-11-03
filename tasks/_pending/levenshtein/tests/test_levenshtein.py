from levenshtein import levenshtein


def test_levenshtein_1():
    assert levenshtein(*['electron', 'neutron']) == 3


def test_levenshtein_2():
    assert levenshtein(*['kitten', 'sitting']) == 3


def test_levenshtein_3():
    assert levenshtein(*['rosettacode', 'raisethysword']) == 8


def test_levenshtein_4():
    assert levenshtein(*['amanaplanacanalpanama', 'docnoteidissentafastneverpreventsafatnessidietoncod']) == 42


def test_levenshtein_5():
    assert levenshtein(*['abcdefg', 'gabcdef']) == 2


def test_levenshtein_6():
    assert levenshtein(*['', '']) == 0


def test_levenshtein_7():
    assert levenshtein(*['hello', 'olleh']) == 4

