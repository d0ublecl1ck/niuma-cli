"""标签配置和历史数据迁移。"""

from __future__ import annotations

from sqlite3 import Connection

from niuma_cli.config import ConfigStore
from niuma_cli.services import progress, todos


def list_tags(config_store: ConfigStore) -> list[str]:
    """列出当前可用标签。"""

    return config_store.load().tags


def add_tag(config_store: ConfigStore, tag_name: str) -> list[str]:
    """新增标签并返回更新后的标签列表。"""

    tag = _normalize_tag(tag_name)
    tags = config_store.load().tags
    if tag in tags:
        raise ValueError(f"标签已存在: {tag}")
    return config_store.save_tags([*tags, tag]).tags


def delete_tag(conn: Connection, config_store: ConfigStore, tag_name: str) -> list[str]:
    """删除未被历史数据引用的标签。"""

    tag = _normalize_tag(tag_name)
    tags = config_store.load().tags
    if tag not in tags:
        raise ValueError(f"标签不存在: {tag}")
    refs = todos.count_tag_references(conn, tag) + progress.count_tag_references(conn, tag)
    if refs:
        raise ValueError(f"标签 [{tag}] 正在被 {refs} 条记录使用，无法删除。请先执行 rename 迁移。")
    return config_store.save_tags([item for item in tags if item != tag]).tags


def rename_tag(conn: Connection, config_store: ConfigStore, old_name: str, new_name: str) -> list[str]:
    """重命名标签并同步迁移 Todo 和 Progress 历史数据。"""

    old_tag = _normalize_tag(old_name)
    new_tag = _normalize_tag(new_name)
    tags = config_store.load().tags
    if old_tag not in tags:
        raise ValueError(f"标签不存在: {old_tag}")
    if new_tag in tags:
        raise ValueError(f"标签已存在: {new_tag}")
    todos.rename_tag(conn, old_tag, new_tag)
    progress.rename_tag(conn, old_tag, new_tag)
    return config_store.save_tags([new_tag if tag == old_tag else tag for tag in tags]).tags


def validate_tag(config_store: ConfigStore, tag_name: str | None) -> str:
    """校验标签，未传时选用第一个默认标签。"""

    tags = config_store.load().tags
    if not tags:
        raise ValueError("当前没有可用标签，请先执行 niuma config tags add <tag_name>")
    if tag_name is None:
        # 当前 V1 使用无阻塞默认值，后续可替换为交互式单选。
        return tags[0]
    tag = _normalize_tag(tag_name)
    if tag not in tags:
        raise ValueError(f"标签不存在: {tag}。请先执行 niuma config tags add {tag}")
    return tag


def _normalize_tag(value: str) -> str:
    """规范化标签输入。"""

    tag = value.strip()
    if not tag:
        raise ValueError("标签不能为空")
    return tag
