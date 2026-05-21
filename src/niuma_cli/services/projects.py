"""项目管理业务。"""

from __future__ import annotations

from sqlite3 import Connection, IntegrityError, Row

from niuma_cli.time_utils import now_text


def create_project(conn: Connection, name: str) -> int:
    """创建项目并返回项目 ID。"""

    normalized = name.strip()
    if not normalized:
        raise ValueError("项目名称不能为空")
    timestamp = now_text()
    try:
        cursor = conn.execute(
            "INSERT INTO projects (name, created_at, updated_at) VALUES (?, ?, ?)",
            (normalized, timestamp, timestamp),
        )
    except IntegrityError as exc:
        raise ValueError(f"项目已存在: {normalized}") from exc
    return int(cursor.lastrowid)


def list_projects(conn: Connection) -> list[Row]:
    """按创建顺序列出项目。"""

    return list(conn.execute("SELECT id, name, created_at, updated_at FROM projects ORDER BY id ASC"))


def get_project(conn: Connection, project_id: int | None) -> Row | None:
    """按 ID 查询项目，空 ID 直接返回 None。"""

    if project_id is None:
        return None
    return conn.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,)).fetchone()


def require_project(conn: Connection, project_id: int | None) -> int | None:
    """校验项目是否存在，允许不关联项目。"""

    if project_id is None:
        return None
    if get_project(conn, project_id) is None:
        raise ValueError(f"项目不存在: {project_id}")
    return project_id
