"""在项目根目录点运行就行（PyCharm 里直接用这个文件）。

等价于 python -m fbs.agent。

必须从项目根目录运行——tasks/ runs/ run_traces/ 都是相对路径。
"""
from fbs.agent import main

main()
