"""终端输出格式化工具。"""

from __future__ import annotations

from collections.abc import Sequence


def render_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """渲染简单 ASCII 表格，保持终端输出可复制。"""

    normalized = [[str(cell) for cell in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in normalized:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    header_line = "| " + " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)) + " |"
    lines = [border, header_line, border]
    for row in normalized:
        lines.append("| " + " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)) + " |")
    lines.append(border)
    return "\n".join(lines)
