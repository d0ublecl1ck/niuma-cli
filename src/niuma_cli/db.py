"""SQLite 连接、建表迁移和事务边界。"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


TABLE_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    content TEXT,
    tag TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'done')),
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    todo_id INTEGER REFERENCES todos(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    content TEXT,
    tag TEXT NOT NULL,
    source TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dailies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    content TEXT NOT NULL,
    raw_context TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS active_sessions (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    kind TEXT NOT NULL CHECK (kind IN ('focus', 'chill')),
    todo_id INTEGER REFERENCES todos(id) ON DELETE SET NULL,
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    tag TEXT NOT NULL,
    started_at TEXT NOT NULL
);
"""

INDEX_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_todos_created_at ON todos(created_at);
CREATE INDEX IF NOT EXISTS idx_todos_completed_at ON todos(completed_at);
CREATE INDEX IF NOT EXISTS idx_progress_created_at ON progress(created_at);
CREATE INDEX IF NOT EXISTS idx_dailies_date ON dailies(date);
"""

LEGACY_TODO_COLUMNS = {"id", "project_id", "content", "tag", "status", "created_at", "completed_at"}
LEGACY_PROGRESS_COLUMNS = {
    "id",
    "project_id",
    "todo_id",
    "content",
    "tag",
    "source",
    "started_at",
    "ended_at",
    "created_at",
}


class Database:
    """封装 SQLite 生命周期，让业务层只关心连接对象。"""

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser()

    def initialize(self) -> None:
        """确保数据库目录和表结构存在。"""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(TABLE_SCHEMA)
            _migrate_title_content_schema(conn)
            conn.executescript(INDEX_SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """提供带事务的连接上下文。"""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _migrate_title_content_schema(conn: sqlite3.Connection) -> None:
    """将旧版 content 单字段表迁移为 title/content 双字段表。"""

    todo_columns = _table_columns(conn, "todos")
    progress_columns = _table_columns(conn, "progress")
    should_migrate_todos = "title" not in todo_columns and LEGACY_TODO_COLUMNS.issubset(todo_columns)
    should_migrate_progress = "title" not in progress_columns and LEGACY_PROGRESS_COLUMNS.issubset(progress_columns)
    if not should_migrate_todos and not should_migrate_progress:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    if should_migrate_todos:
        _rebuild_legacy_todos(conn)
    if should_migrate_progress:
        _rebuild_legacy_progress(conn)
    conn.execute("PRAGMA foreign_keys = ON")


def _rebuild_legacy_todos(conn: sqlite3.Connection) -> None:
    """重建旧 Todo 表，把旧 content 全量迁移为 title。"""

    conn.execute("ALTER TABLE todos RENAME TO todos_legacy")
    conn.execute(
        """
        CREATE TABLE todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            content TEXT,
            tag TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('pending', 'done')),
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO todos (id, project_id, title, content, tag, status, created_at, completed_at)
        SELECT id, project_id, content, NULL, tag, status, created_at, completed_at
        FROM todos_legacy
        """
    )
    conn.execute("DROP TABLE todos_legacy")


def _rebuild_legacy_progress(conn: sqlite3.Connection) -> None:
    """重建旧 Progress 表，把旧 content 全量迁移为 title。"""

    conn.execute("ALTER TABLE progress RENAME TO progress_legacy")
    conn.execute(
        """
        CREATE TABLE progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
            todo_id INTEGER REFERENCES todos(id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            content TEXT,
            tag TEXT NOT NULL,
            source TEXT NOT NULL,
            started_at TEXT,
            ended_at TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO progress (id, project_id, todo_id, title, content, tag, source, started_at, ended_at, created_at)
        SELECT id, project_id, todo_id, content, NULL, tag, source, started_at, ended_at, created_at
        FROM progress_legacy
        """
    )
    conn.execute("DROP TABLE progress_legacy")


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    """读取表字段名，供轻量迁移判断使用。"""

    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})")}
