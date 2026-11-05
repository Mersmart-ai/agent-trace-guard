"""导出成 CSV，给机器读。"""

from report import format_size


def export_csv(rows):
    """[(名字, 字节数)] → CSV 文本。

    大小列用的是 format_size 的结果，不含原始字节数——
    下游的报表工具按这个格式解析，不能改。
    """
    lines = ["name,size"]
    for name, size in rows:
        lines.append(f"{name},{format_size(size)}")
    return "\n".join(lines)
