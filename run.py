"""在项目根目录点运行就行（PyCharm 里直接用这个文件）。

等价于 PYTHONPATH=src python -m fbs.cli。

必须从项目根目录运行——tasks/ runs/ data/ 都是相对路径。
"""
import sys
from pathlib import Path

# 允许直接 python run.py（不必先 pip install -e .）
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from fbs.cli import main

main()
