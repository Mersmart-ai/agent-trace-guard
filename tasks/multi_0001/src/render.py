"""渲染报表里的一行。

下游的报表工具按 "名字         大小" 的格式解析，大小那一列不能带别的修饰。
"""

from formatter import format_size


def render(name, size):
    return f"{name:<12}{format_size(size)}"
