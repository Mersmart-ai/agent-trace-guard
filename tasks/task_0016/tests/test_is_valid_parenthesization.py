from is_valid_parenthesization import is_valid_parenthesization


def test_1():
    assert is_valid_parenthesization(*['((()()))()']) == True


def test_2():
    assert is_valid_parenthesization(*[')()(']) == False


def test_3():
    assert is_valid_parenthesization(*['((']) == False

