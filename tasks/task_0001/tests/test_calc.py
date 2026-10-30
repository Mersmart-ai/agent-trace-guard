from calc import add, mean, multiply
import pytest
def test_add_positive():
    assert add(2, 3) == 5
def test_add_negative():
    assert add(-1,-2) ==-3
def test_mean():
    assert mean([1,2,3,4]) == pytest.approx(2.5)
def test_multiply():
    assert multiply(2,3) == 6


