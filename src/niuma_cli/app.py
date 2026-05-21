"""应用运行时依赖组装。"""

from __future__ import annotations

from dataclasses import dataclass

from niuma_cli.config import ConfigStore
from niuma_cli.db import Database


@dataclass(frozen=True)
class AppContext:
    """CLI 命令共享的运行上下文。"""

    config_store: ConfigStore
    database: Database


def create_app_context(initialize_database: bool = True) -> AppContext:
    """从本地配置构建运行上下文，并按命令需要初始化数据库。"""

    config_store = ConfigStore()
    config = config_store.load()
    database = Database(config.db_path)
    if initialize_database:
        database.initialize()
    return AppContext(config_store=config_store, database=database)
