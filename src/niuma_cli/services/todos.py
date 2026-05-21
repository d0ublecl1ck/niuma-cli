"""Todo 管理业务。"""

from __future__ import annotations

from sqlite3 import Connection, Row

from niuma_cli.services.progress import create_progress
from niuma_cli.services.projects import require_project
from niuma_cli.time_utils import now_text, validate_date


TODO_DONE_PROGRESS_PREFIX = "【已完成 Todo】"


def create_todo(conn: Connection, content: str, tag: str, project_id: int | None = None) -> int:
    """创建待办任务。"""

    normalized = content.strip()
    if not normalized:
        raise ValueError("Todo 内容不能为空")
    require_project(conn, project_id)
    cursor = conn.execute(
        """
        INSERT INTO todos (project_id, content, tag, status, created_at, completed_at)
        VALUES (?, ?, ?, 'pending', ?, NULL)
        """,
        (project_id, normalized, tag, now_text()),
    )
    return int(cursor.lastrowid)


def complete_todo(conn: Connection, todo_id: int) -> int:
    """完成 Todo，并自动物化为 Progress 流水账。"""

    todo = conn.execute(
        "SELECT id, project_id, content, tag, status FROM todos WHERE id = ?",
        (todo_id,),
    ).fetchone()
    if todo is None:
        raise ValueError(f"Todo 不存在: {todo_id}")
    if todo["status"] == "done":
        raise ValueError(f"Todo 已完成: {todo_id}")

    timestamp = now_text()
    conn.execute(
        "UPDATE todos SET status = 'done', completed_at = ? WHERE id = ?",
        (timestamp, todo_id),
    )
    return create_progress(
        conn=conn,
        content=f"{TODO_DONE_PROGRESS_PREFIX}{todo['content']}",
        tag=todo["tag"],
        project_id=todo["project_id"],
        todo_id=todo["id"],
        source="todo_done",
        created_at=timestamp,
    )


def list_todos(conn: Connection, date_text: str | None = None) -> dict[str, list[Row]]:
    """按项目分组所需数据的上游查询，CLI 层负责展示分区。"""

    day = validate_date(date_text)
    pending = _query_todos(conn, "status = 'pending'", ())
    created = _query_todos(conn, "date(t.created_at) = ?", (day,))
    completed = _query_todos(conn, "date(t.completed_at) = ?", (day,))
    return {"pending": pending, "created": created, "completed": completed}


def count_today(conn: Connection) -> tuple[int, int]:
    """统计今日完成和当前未完成任务数。"""

    today = validate_date(None)
    completed = conn.execute(
        "SELECT COUNT(*) AS count FROM todos WHERE date(completed_at) = ?",
        (today,),
    ).fetchone()["count"]
    pending = conn.execute("SELECT COUNT(*) AS count FROM todos WHERE status = 'pending'").fetchone()["count"]
    return int(completed), int(pending)


def count_tag_references(conn: Connection, tag: str) -> int:
    """统计标签在 Todo 中的引用数量。"""

    row = conn.execute("SELECT COUNT(*) AS count FROM todos WHERE tag = ?", (tag,)).fetchone()
    return int(row["count"])


def rename_tag(conn: Connection, old_name: str, new_name: str) -> None:
    """迁移 Todo 历史标签。"""

    conn.execute("UPDATE todos SET tag = ? WHERE tag = ?", (new_name, old_name))


def _query_todos(conn: Connection, where_clause: str, params: tuple[object, ...]) -> list[Row]:
    """统一 Todo 查询字段，避免展示层依赖表结构细节。"""

    return list(
        conn.execute(
            f"""
            SELECT t.id, t.content, t.tag, t.status, t.created_at, t.completed_at, p.name AS project_name
            FROM todos t
            LEFT JOIN projects p ON p.id = t.project_id
            WHERE {where_clause}
            ORDER BY COALESCE(t.completed_at, t.created_at) ASC, t.id ASC
            """,
            params,
        )
    )
