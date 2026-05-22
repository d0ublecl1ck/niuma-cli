"""跨实体模糊搜索业务。"""

from __future__ import annotations

from dataclasses import dataclass
from sqlite3 import Connection

from niuma_cli.config import ConfigStore


SEARCH_ENTITIES = ("project", "todo", "progress", "daily", "tag")


@dataclass(frozen=True)
class SearchResult:
    """统一表达不同实体的搜索命中结果。"""

    entity: str
    entity_id: str
    title: str
    matched_field: str
    content: str | None
    recorded_at: str | None


def search_all(conn: Connection, config_store: ConfigStore, query: str, entity: str = "all") -> list[SearchResult]:
    """按关键词在指定实体或全部实体中做模糊搜索。"""

    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("搜索关键词不能为空")
    if entity != "all" and entity not in SEARCH_ENTITIES:
        raise ValueError(f"不支持的搜索实体: {entity}")

    pattern = f"%{_escape_like(normalized_query)}%"
    results: list[SearchResult] = []
    if entity in {"all", "project"}:
        results.extend(_search_projects(conn, pattern))
    if entity in {"all", "todo"}:
        results.extend(_search_todos(conn, pattern))
    if entity in {"all", "progress"}:
        results.extend(_search_progress(conn, pattern))
    if entity in {"all", "daily"}:
        results.extend(_search_dailies(conn, pattern))
    if entity in {"all", "tag"}:
        results.extend(_search_tags(config_store, normalized_query))
    return results


def _search_projects(conn: Connection, pattern: str) -> list[SearchResult]:
    """搜索项目名称。"""

    rows = conn.execute(
        """
        SELECT id, name, created_at
        FROM projects
        WHERE lower(name) LIKE lower(?) ESCAPE '\\'
        ORDER BY id ASC
        """,
        (pattern,),
    )
    return [
        SearchResult("project", str(row["id"]), row["name"], "name", None, row["created_at"])
        for row in rows
    ]


def _search_todos(conn: Connection, pattern: str) -> list[SearchResult]:
    """搜索 Todo 标题、内容、标签、状态和项目名。"""

    rows = conn.execute(
        """
        SELECT t.id, t.title, t.content, t.tag, t.status, t.created_at, p.name AS project_name,
               CASE
                   WHEN lower(t.title) LIKE lower(?) ESCAPE '\\' THEN 'title'
                   WHEN lower(COALESCE(t.content, '')) LIKE lower(?) ESCAPE '\\' THEN 'content'
                   WHEN lower(t.tag) LIKE lower(?) ESCAPE '\\' THEN 'tag'
                   WHEN lower(t.status) LIKE lower(?) ESCAPE '\\' THEN 'status'
                   ELSE 'project'
               END AS matched_field
        FROM todos t
        LEFT JOIN projects p ON p.id = t.project_id
        WHERE lower(t.title) LIKE lower(?) ESCAPE '\\'
           OR lower(COALESCE(t.content, '')) LIKE lower(?) ESCAPE '\\'
           OR lower(t.tag) LIKE lower(?) ESCAPE '\\'
           OR lower(t.status) LIKE lower(?) ESCAPE '\\'
           OR lower(COALESCE(p.name, '')) LIKE lower(?) ESCAPE '\\'
        ORDER BY t.created_at ASC, t.id ASC
        """,
        (pattern, pattern, pattern, pattern, pattern, pattern, pattern, pattern, pattern),
    )
    return [
        SearchResult("todo", str(row["id"]), row["title"], row["matched_field"], row["content"], row["created_at"])
        for row in rows
    ]


def _search_progress(conn: Connection, pattern: str) -> list[SearchResult]:
    """搜索 Progress 标题、内容、标签、来源和项目名。"""

    rows = conn.execute(
        """
        SELECT p.id, p.title, p.content, p.tag, p.source, p.happened_at, pr.name AS project_name,
               CASE
                   WHEN lower(p.title) LIKE lower(?) ESCAPE '\\' THEN 'title'
                   WHEN lower(COALESCE(p.content, '')) LIKE lower(?) ESCAPE '\\' THEN 'content'
                   WHEN lower(p.tag) LIKE lower(?) ESCAPE '\\' THEN 'tag'
                   WHEN lower(p.source) LIKE lower(?) ESCAPE '\\' THEN 'source'
                   ELSE 'project'
               END AS matched_field
        FROM progress p
        LEFT JOIN projects pr ON pr.id = p.project_id
        WHERE lower(p.title) LIKE lower(?) ESCAPE '\\'
           OR lower(COALESCE(p.content, '')) LIKE lower(?) ESCAPE '\\'
           OR lower(p.tag) LIKE lower(?) ESCAPE '\\'
           OR lower(p.source) LIKE lower(?) ESCAPE '\\'
           OR lower(COALESCE(pr.name, '')) LIKE lower(?) ESCAPE '\\'
        ORDER BY p.happened_at ASC, p.id ASC
        """,
        (pattern, pattern, pattern, pattern, pattern, pattern, pattern, pattern, pattern),
    )
    return [SearchResult("progress", str(row["id"]), row["title"], row["matched_field"], row["content"], row["happened_at"]) for row in rows]


def _search_dailies(conn: Connection, pattern: str) -> list[SearchResult]:
    """搜索日报日期、正文和原始上下文。"""

    rows = conn.execute(
        """
        SELECT id, date, content, created_at,
               CASE
                   WHEN lower(date) LIKE lower(?) ESCAPE '\\' THEN 'date'
                   WHEN lower(content) LIKE lower(?) ESCAPE '\\' THEN 'content'
                   ELSE 'raw_context'
               END AS matched_field
        FROM dailies
        WHERE lower(date) LIKE lower(?) ESCAPE '\\'
           OR lower(content) LIKE lower(?) ESCAPE '\\'
           OR lower(raw_context) LIKE lower(?) ESCAPE '\\'
        ORDER BY created_at ASC, id ASC
        """,
        (pattern, pattern, pattern, pattern, pattern),
    )
    return [
        SearchResult("daily", str(row["id"]), row["date"], row["matched_field"], row["content"], row["created_at"])
        for row in rows
    ]


def _search_tags(config_store: ConfigStore, query: str) -> list[SearchResult]:
    """搜索配置里的标签实体。"""

    lowered_query = query.casefold()
    return [
        SearchResult("tag", tag, tag, "name", None, None)
        for tag in config_store.load().tags
        if lowered_query in tag.casefold()
    ]


def _escape_like(value: str) -> str:
    """转义 LIKE 通配符，让用户输入按普通文本搜索。"""

    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
