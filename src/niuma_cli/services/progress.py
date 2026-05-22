"""Progress 流水账业务。"""

from __future__ import annotations

from sqlite3 import Connection, Row

from niuma_cli.services.projects import require_project
from niuma_cli.time_utils import now_text, validate_date


def create_progress(
    conn: Connection,
    title: str,
    tag: str,
    project_id: int | None = None,
    todo_id: int | None = None,
    source: str = "manual",
    created_at: str | None = None,
    started_at: str | None = None,
    ended_at: str | None = None,
    content: str | None = None,
) -> int:
    """创建一条工作进度记录，标题必填，内容详情可选。"""

    normalized_title = title.strip()
    normalized_content = _normalize_optional_content(content)
    if not normalized_title:
        raise ValueError("Progress 标题不能为空")
    require_project(conn, project_id)
    timestamp = created_at or now_text()
    cursor = conn.execute(
        """
        INSERT INTO progress (project_id, todo_id, title, content, tag, source, started_at, ended_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (project_id, todo_id, normalized_title, normalized_content, tag, source, started_at, ended_at, timestamp),
    )
    return int(cursor.lastrowid)


def list_progress(conn: Connection, date_text: str | None = None) -> list[Row]:
    """按指定日期列出手动和自动生成的流水账。"""

    day = validate_date(date_text)
    return list(
        conn.execute(
            """
            SELECT p.id, p.title, p.content, p.tag, p.source, p.created_at, pr.name AS project_name
            FROM progress p
            LEFT JOIN projects pr ON pr.id = p.project_id
            WHERE date(p.created_at) = ?
            ORDER BY p.created_at ASC, p.id ASC
            """,
            (day,),
        )
    )


def modify_progress(
    conn: Connection,
    progress_id: int,
    title: str | None = None,
    content: str | None = None,
    tag: str | None = None,
    project_id: int | None = None,
    change_project: bool = False,
) -> None:
    """按需更新 Progress 标题、内容详情、标签和项目关联。"""

    progress = conn.execute("SELECT id FROM progress WHERE id = ?", (progress_id,)).fetchone()
    if progress is None:
        raise ValueError(f"Progress 不存在: {progress_id}")
    if title is None and content is None and tag is None and not change_project:
        raise ValueError("请至少提供一个要更新的 Progress 字段")

    updates: list[str] = []
    params: list[object] = []
    if title is not None:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("Progress 标题不能为空")
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

    params.append(progress_id)
    conn.execute(f"UPDATE progress SET {', '.join(updates)} WHERE id = ?", params)


def count_tag_references(conn: Connection, tag: str) -> int:
    """统计标签在 Progress 中的引用数量。"""

    row = conn.execute("SELECT COUNT(*) AS count FROM progress WHERE tag = ?", (tag,)).fetchone()
    return int(row["count"])


def rename_tag(conn: Connection, old_name: str, new_name: str) -> None:
    """迁移 Progress 历史标签。"""

    conn.execute("UPDATE progress SET tag = ? WHERE tag = ?", (new_name, old_name))


def _normalize_optional_content(content: str | None) -> str | None:
    """规范化可选详情，空白详情按未填写处理。"""

    if content is None:
        return None
    normalized = content.strip()
    return normalized or None
