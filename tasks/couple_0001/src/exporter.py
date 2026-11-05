"""导出成 CSV，给机器读。"""

from report import format_size


def export_csv(rows):
    """[(名字, 字节数)] → CSV 文本。"""
    lines = ["name,size"]
    for name, size in rows:
        lines.append(f"{name},{format_size(size)}")
    return "\n".join(lines)
