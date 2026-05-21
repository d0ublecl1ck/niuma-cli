"""配置文件读写与默认路径解析。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_TAGS = ["Feature", "Bug", "Refactor", "Meeting", "Support", "Research"]


@dataclass(frozen=True)
class AppConfig:
    """集中表达 CLI 运行所需配置，避免命令层直接拼接路径。"""

    db_path: Path
    tags: list[str]


class ConfigStore:
    """负责加载、保存和迁移本地 JSON 配置。"""

    def __init__(self, home_dir: Path | None = None) -> None:
        # NIUMA_HOME 仅用于测试或高级用户隔离数据目录，默认仍遵循文档写入用户家目录。
        self.home_dir = home_dir or Path(os.environ.get("NIUMA_HOME", Path.home() / ".niuma")).expanduser()
        self.config_path = self.home_dir / "config.json"

    @property
    def default_db_path(self) -> Path:
        """返回默认 SQLite 路径。"""

        return self.home_dir / "niuma.db"

    def load(self) -> AppConfig:
        """加载配置；缺失时返回默认配置但不强制写盘。"""

        raw = self._read_raw()
        db_path = Path(raw.get("db", {}).get("path") or self.default_db_path).expanduser()
        tags = raw["tags"] if "tags" in raw else DEFAULT_TAGS
        return AppConfig(db_path=db_path, tags=list(dict.fromkeys(str(tag) for tag in tags if str(tag).strip())))

    def get(self, key: str) -> str:
        """读取支持的配置项。"""

        config = self.load()
        if key == "db.path":
            return str(config.db_path)
        raise KeyError(f"不支持的配置项: {key}")

    def set_db_path(self, value: str) -> AppConfig:
        """保存数据库路径配置。"""

        raw = self._read_raw()
        raw.setdefault("db", {})["path"] = str(Path(value).expanduser())
        self._write_raw(raw)
        return self.load()

    def reset(self) -> AppConfig:
        """恢复默认配置，保留标签列表并重置数据库路径。"""

        raw = self._read_raw()
        raw.setdefault("db", {})["path"] = str(self.default_db_path)
        raw["tags"] = raw["tags"] if "tags" in raw else DEFAULT_TAGS
        self._write_raw(raw)
        return self.load()

    def save_tags(self, tags: list[str]) -> AppConfig:
        """保存去重后的标签列表。"""

        normalized = [tag.strip() for tag in tags if tag.strip()]
        if not normalized:
            raise ValueError("至少需要保留一个标签")
        raw = self._read_raw()
        raw["tags"] = list(dict.fromkeys(normalized))
        raw.setdefault("db", {})["path"] = str(self.load().db_path)
        self._write_raw(raw)
        return self.load()

    def _read_raw(self) -> dict[str, Any]:
        """读取原始 JSON，损坏时显式报错以避免覆盖用户配置。"""

        if not self.config_path.exists():
            return {"db": {"path": str(self.default_db_path)}, "tags": DEFAULT_TAGS}
        with self.config_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError(f"配置文件格式错误: {self.config_path}")
        return data

    def _write_raw(self, data: dict[str, Any]) -> None:
        """原子化写入配置，降低异常中断导致配置损坏的概率。"""

        self.home_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self.config_path.with_suffix(".json.tmp")
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        tmp_path.replace(self.config_path)
