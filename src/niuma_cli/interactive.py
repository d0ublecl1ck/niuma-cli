"""终端交互选择工具。"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from sqlite3 import Row


def choose_tag(tags: Sequence[str], provided_tag: str | None) -> str | None:
    """未传标签且处于交互终端时，让用户选择任务类型。"""

    if provided_tag is not None or not sys.stdin.isatty():
        return provided_tag
    choice = _choose("请选择任务类型", list(tags), allow_none=False)
    return choice


def choose_project_id(projects: Sequence[Row], provided_project_id: int | None) -> int | None:
    """未传项目且处于交互终端时，让用户选择关联项目或跳过。"""

    if provided_project_id is not None or not sys.stdin.isatty() or not projects:
        return provided_project_id
    labels = [f"#{row['id']} {row['name']}" for row in projects]
    selected = _choose("请选择关联项目", labels, allow_none=True)
    if selected is None:
        return None
    return int(selected.split(" ", maxsplit=1)[0].lstrip("#"))


def _choose(prompt: str, options: list[str], allow_none: bool) -> str | None:
    """用数字菜单实现零依赖单选交互。"""

    print(f"? {prompt}:")
    start_index = 1
    if allow_none:
        print("0. 不关联")
    for offset, option in enumerate(options, start=start_index):
        print(f"{offset}. {option}")

    while True:
        raw = input("请输入编号: ").strip()
        if allow_none and raw == "0":
            return None
        if raw.isdigit():
            index = int(raw) - 1
            if 0 <= index < len(options):
                return options[index]
        print("输入无效，请重新选择。")
