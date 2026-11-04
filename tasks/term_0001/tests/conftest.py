import os
from pathlib import Path

import pytest


@pytest.fixture
def ws():
    """工作区路径。

    run_tests 会把 PYTHONPATH 覆盖成工作区的绝对路径，所以第一个就是它。
    不能靠相对路径——pytest 的当前目录是项目根，不是工作区。
    """
    return Path(os.environ["PYTHONPATH"].split(os.pathsep)[0])
