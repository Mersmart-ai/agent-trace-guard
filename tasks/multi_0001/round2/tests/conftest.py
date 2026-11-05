import os
from pathlib import Path
import pytest

@pytest.fixture
def ws():
    return Path(os.environ["PYTHONPATH"].split(os.pathsep)[0])
