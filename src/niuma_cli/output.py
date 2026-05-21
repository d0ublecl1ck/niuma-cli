"""终端输出格式化工具。"""

from __future__ import annotations

from collections.abc import Sequence

from prettytable import PrettyTable


def render_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """使用 PrettyTable 渲染终端表格，保持输出宽度对齐。"""

    table = PrettyTable()
    table.field_names = [str(header) for header in headers]
    for row in rows:
        table.add_row([str(cell) for cell in row])
    return table.get_string()
