"""Progress 流水账业务。"""

from __future__ import annotations

from sqlite3 import Connection, Row

from niuma_cli.services.projects import require_project
from niuma_cli.time_utils import now_text, validate_date


def create_progress(
    conn: Connection,
    content: str,
    tag: str,
    project_id: int | None = None,
    todo_id: int | None = None,
    source: str = "manual",
    created_at: str | None = None,
) -> int:
    """创建一条工作进度记录。"""

    normalized = content.strip()
    if not normalized:
        raise ValueError("Progress 内容不能为空")
    require_project(conn, project_id)
    timestamp = created_at or now_text()
    cursor = conn.execute(
        """
        INSERT INTO progress (project_id, todo_id, content, tag, source, started_at, ended_at, created_at)
        VALUES (?, ?, ?, ?, ?, NULL, NULL, ?)
        """,
        (project_id, todo_id, normalized, tag, source, timestamp),
    )
    return int(cursor.lastrowid)


def list_progress(conn: Connection, date_text: str | None = None) -> list[Row]:
    """按指定日期列出手动和自动生成的流水账。"""

    day = validate_date(date_text)
    return list(
        conn.execute(
            """
            SELECT p.id, p.content, p.tag, p.source, p.created_at, pr.name AS project_name
            FROM progress p
            LEFT JOIN projects pr ON pr.id = p.project_id
            WHERE date(p.created_at) = ?
            ORDER BY p.created_at ASC, p.id ASC
            """,
            (day,),
        )
    )


def count_tag_references(conn: Connection, tag: str) -> int:
    """统计标签在 Progress 中的引用数量。"""

    row = conn.execute("SELECT COUNT(*) AS count FROM progress WHERE tag = ?", (tag,)).fetchone()
    return int(row["count"])


def rename_tag(conn: Connection, old_name: str, new_name: str) -> None:
    """迁移 Progress 历史标签。"""

    conn.execute("UPDATE progress SET tag = ? WHERE tag = ?", (new_name, old_name))
