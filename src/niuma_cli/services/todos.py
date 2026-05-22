"""Todo 管理业务。"""

from __future__ import annotations

from sqlite3 import Connection, Row

from niuma_cli.services.progress import create_progress
from niuma_cli.services.projects import require_project
from niuma_cli.time_utils import now_text, validate_date


TODO_DONE_PROGRESS_PREFIX = "【已完成 Todo】"


def create_todo(conn: Connection, title: str, tag: str, project_id: int | None = None, content: str | None = None) -> int:
    """创建待办任务，标题必填，内容详情可选。"""

    normalized_title = title.strip()
    normalized_content = _normalize_optional_content(content)
    if not normalized_title:
        raise ValueError("Todo 标题不能为空")
    require_project(conn, project_id)
    cursor = conn.execute(
        """
        INSERT INTO todos (project_id, title, content, tag, status, created_at, completed_at)
        VALUES (?, ?, ?, ?, 'pending', ?, NULL)
        """,
        (project_id, normalized_title, normalized_content, tag, now_text()),
    )
    return int(cursor.lastrowid)


def complete_todo(conn: Connection, todo_id: int) -> int:
    """完成 Todo，并自动物化为 Progress 流水账。"""

    todo = conn.execute(
        "SELECT id, project_id, title, content, tag, status FROM todos WHERE id = ?",
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
        title=f"{TODO_DONE_PROGRESS_PREFIX}{todo['title']}",
        content=todo["content"],
        tag=todo["tag"],
        project_id=todo["project_id"],
        todo_id=todo["id"],
        source="todo_done",
        created_at=timestamp,
    )


def modify_todo(
    conn: Connection,
    todo_id: int,
    title: str | None = None,
    content: str | None = None,
    tag: str | None = None,
    project_id: int | None = None,
    change_project: bool = False,
) -> None:
    """按需更新 Todo 标题、内容详情、标签和项目关联。"""

    todo = conn.execute("SELECT id FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if todo is None:
        raise ValueError(f"Todo 不存在: {todo_id}")
    if title is None and content is None and tag is None and not change_project:
        raise ValueError("请至少提供一个要更新的 Todo 字段")

    updates: list[str] = []
    params: list[object] = []
    if title is not None:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("Todo 标题不能为空")
        updates.append("title = ?")
        params.append(normalized_title)
    if content is not None:
        normalized = _normalize_optional_content(content)
        updates.append("content = ?")
        params.append(normalized)
    if tag is not None:
        updates.append("tag = ?")
        params.append(tag)
    if change_project:
        require_project(conn, project_id)
        updates.append("project_id = ?")
        params.append(project_id)

    params.append(todo_id)
    conn.execute(f"UPDATE todos SET {', '.join(updates)} WHERE id = ?", params)


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
            SELECT t.id, t.title, t.content, t.tag, t.status, t.created_at, t.completed_at, p.name AS project_name
            FROM todos t
            LEFT JOIN projects p ON p.id = t.project_id
            WHERE {where_clause}
            ORDER BY COALESCE(t.completed_at, t.created_at) ASC, t.id ASC
            """,
            params,
        )
    )


def _normalize_optional_content(content: str | None) -> str | None:
    """规范化可选详情，空白详情按未填写处理。"""

    if content is None:
        return None
    normalized = content.strip()
    return normalized or None
