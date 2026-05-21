"""专注计时和 Chill 活动会话业务。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from sqlite3 import Connection

from niuma_cli.services.progress import create_progress
from niuma_cli.time_utils import datetime_text, minutes_between, now_text, parse_duration_minutes, parse_local_datetime


CHILL_TAG = "__chill__"


@dataclass(frozen=True)
class FinishedSession:
    """表达结束活动后生成的 Progress 信息。"""

    progress_id: int
    minutes: int
    content: str


def start_focus(conn: Connection, todo_id: int) -> None:
    """开始专注处理指定 Todo。"""

    _ensure_no_active_session(conn)
    todo = conn.execute(
        "SELECT id, project_id, content, tag, status FROM todos WHERE id = ?",
        (todo_id,),
    ).fetchone()
    if todo is None:
        raise ValueError(f"Todo 不存在: {todo_id}")
    if todo["status"] == "done":
        raise ValueError(f"Todo 已完成，不能开始专注: {todo_id}")
    conn.execute(
        """
        INSERT INTO active_sessions (id, kind, todo_id, project_id, content, tag, started_at)
        VALUES (1, 'focus', ?, ?, ?, ?, ?)
        """,
        (todo["id"], todo["project_id"], todo["content"], todo["tag"], now_text()),
    )


def log_focus(
    conn: Connection,
    todo_id: int,
    started_at_text: str | None = None,
    ended_at_text: str | None = None,
    duration_text: str | None = None,
) -> FinishedSession:
    """补录指定 Todo 的专注时间。"""

    todo = _require_pending_todo(conn, todo_id)
    started_at, ended_at = _resolve_manual_time_range(started_at_text, ended_at_text, duration_text)
    minutes = minutes_between(started_at, ended_at)
    content = f"【专注补录】耗时 {minutes} 分钟推进了该任务：{todo['content']}"
    progress_id = create_progress(
        conn=conn,
        content=content,
        tag=todo["tag"],
        project_id=todo["project_id"],
        todo_id=todo["id"],
        source="focus",
        created_at=ended_at,
        started_at=started_at,
        ended_at=ended_at,
    )
    return FinishedSession(progress_id=progress_id, minutes=minutes, content=content)


def stop_focus(conn: Connection) -> FinishedSession:
    """结束当前专注计时并生成 Progress。"""

    session = _require_active_session(conn, "focus")
    ended_at = now_text()
    minutes = minutes_between(session["started_at"], ended_at)
    content = f"【专注】耗时 {minutes} 分钟推进了该任务：{session['content']}"
    progress_id = create_progress(
        conn=conn,
        content=content,
        tag=session["tag"],
        project_id=session["project_id"],
        todo_id=session["todo_id"],
        source="focus",
        created_at=ended_at,
        started_at=session["started_at"],
        ended_at=ended_at,
    )
    _clear_active_session(conn)
    return FinishedSession(progress_id=progress_id, minutes=minutes, content=content)


def start_chill(conn: Connection, content: str) -> None:
    """开始记录一段非工作或等待状态。"""

    _ensure_no_active_session(conn)
    normalized = content.strip()
    if not normalized:
        raise ValueError("Chill 内容不能为空")
    conn.execute(
        """
        INSERT INTO active_sessions (id, kind, todo_id, project_id, content, tag, started_at)
        VALUES (1, 'chill', NULL, NULL, ?, ?, ?)
        """,
        (normalized, CHILL_TAG, now_text()),
    )


def end_chill(conn: Connection) -> FinishedSession:
    """结束当前 Chill 记录并生成 Progress。"""

    session = _require_active_session(conn, "chill")
    ended_at = now_text()
    minutes = minutes_between(session["started_at"], ended_at)
    content = f"【Chill】耗时 {minutes} 分钟：{session['content']}"
    progress_id = create_progress(
        conn=conn,
        content=content,
        tag=session["tag"],
        source="chill",
        created_at=ended_at,
        started_at=session["started_at"],
        ended_at=ended_at,
    )
    _clear_active_session(conn)
    return FinishedSession(progress_id=progress_id, minutes=minutes, content=content)


def _ensure_no_active_session(conn: Connection) -> None:
    """确保当前没有正在进行的活动会话。"""

    row = conn.execute("SELECT kind FROM active_sessions WHERE id = 1").fetchone()
    if row is not None:
        raise ValueError(f"已有进行中的 {row['kind']} 会话，请先结束")


def _require_pending_todo(conn: Connection, todo_id: int):
    """读取可补录专注时间的 Todo。"""

    todo = conn.execute(
        "SELECT id, project_id, content, tag, status FROM todos WHERE id = ?",
        (todo_id,),
    ).fetchone()
    if todo is None:
        raise ValueError(f"Todo 不存在: {todo_id}")
    if todo["status"] == "done":
        raise ValueError(f"Todo 已完成，不能补录专注: {todo_id}")
    return todo


def _resolve_manual_time_range(
    started_at_text: str | None,
    ended_at_text: str | None,
    duration_text: str | None,
) -> tuple[str, str]:
    """解析补录时间范围，支持时间段或时长模式。"""

    if started_at_text and ended_at_text and duration_text:
        raise ValueError("不能同时传入 --from、--to 和 --duration")
    if started_at_text and ended_at_text:
        started_at = parse_local_datetime(started_at_text)
        ended_at = parse_local_datetime(ended_at_text)
    elif duration_text and started_at_text:
        started_at = parse_local_datetime(started_at_text)
        ended_at = started_at + timedelta(minutes=parse_duration_minutes(duration_text))
    elif duration_text and ended_at_text:
        ended_at = parse_local_datetime(ended_at_text)
        started_at = ended_at - timedelta(minutes=parse_duration_minutes(duration_text))
    elif duration_text:
        ended_at = parse_local_datetime(now_text()[:16])
        started_at = ended_at - timedelta(minutes=parse_duration_minutes(duration_text))
    else:
        raise ValueError("请使用 --from/--to 指定时间段，或使用 --duration 指定补录时长")
    if ended_at <= started_at:
        raise ValueError("结束时间必须晚于开始时间")
    return datetime_text(started_at), datetime_text(ended_at)


def _require_active_session(conn: Connection, kind: str):
    """读取指定类型的进行中会话。"""

    row = conn.execute("SELECT * FROM active_sessions WHERE id = 1 AND kind = ?", (kind,)).fetchone()
    if row is None:
        raise ValueError(f"没有进行中的 {kind} 会话")
    return row


def _clear_active_session(conn: Connection) -> None:
    """清除当前活动会话。"""

    conn.execute("DELETE FROM active_sessions WHERE id = 1")


def count_tag_references(conn: Connection, tag: str) -> int:
    """统计标签在进行中活动会话里的引用数量。"""

    row = conn.execute("SELECT COUNT(*) AS count FROM active_sessions WHERE tag = ?", (tag,)).fetchone()
    return int(row["count"])


def rename_tag(conn: Connection, old_name: str, new_name: str) -> None:
    """迁移进行中活动会话的标签。"""

    conn.execute("UPDATE active_sessions SET tag = ? WHERE tag = ?", (new_name, old_name))
