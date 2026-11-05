"""把数据渲染成给人看的表格。"""


def format_size(n, with_bytes=False):
    """字节数 → 人类可读的大小。

    :param n: 字节数
    :param with_bytes: True 时在括号里附上原始字节数，比如 "1.5 KB (1536 B)"
    """
    if n < 1024:
        text = f"{n} B"
    elif n < 1024 ** 2:
        text = f"{n / 1024:.1f} KB"
    else:
        text = f"{n / 1024 ** 2:.1f} MB"
    if with_bytes:
        return f"{text} ({n} B)"
    return text


def render_table(rows):
    """[(名字, 字节数)] → 每行一条的表格文本。"""
    lines = []
    for name, size in rows:
        lines.append(f"{name:<10} {format_size(size)}")
    return "\n".join(lines)
