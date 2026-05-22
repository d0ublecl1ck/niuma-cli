"""日报生成与持久化业务。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from sqlite3 import Connection, Row
from urllib import error, request

from niuma_cli.config import LlmConfig
from niuma_cli.time_utils import now_text, validate_date, week_range


PROMPT_INSTRUCTION = "请将以下程序员的工作流水账，转化成一份结构清晰、用词专业、适合向上级汇报的日报文本。"
CHAT_COMPLETIONS_PATH = "/v1/chat/completions"


@dataclass(frozen=True)
class DailyReport:
    """表达一次日报生成结果，供 CLI 展示和测试断言复用。"""

    daily_id: int
    date: str
    content: str
    raw_context: str


def generate_daily(conn: Connection, date_text: str | None = None, llm_config: LlmConfig | None = None) -> DailyReport:
    """读取指定日期记录，生成日报文本并保存到 dailies 表。"""

    day = validate_date(date_text)
    progress_rows = _list_daily_progress(conn, day)
    completed_todos = _list_completed_todos(conn, day)
    if not progress_rows and not completed_todos:
        raise ValueError(f"{day} 暂无可生成日报的 Progress 或已完成 Todo")

    raw_context = _build_raw_context(day, progress_rows, completed_todos)
    content = (
        _generate_llm_report(raw_context, llm_config)
        if _is_llm_enabled(llm_config)
        else _compose_report(f"{day} 日报", progress_rows, completed_todos, "今日", "一、今日完成")
    )
    cursor = conn.execute(
        """
        INSERT INTO dailies (date, content, raw_context, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (day, content, raw_context, now_text()),
    )
    return DailyReport(daily_id=int(cursor.lastrowid), date=day, content=content, raw_context=raw_context)


def generate_weekly(conn: Connection, date_text: str | None = None, llm_config: LlmConfig | None = None) -> DailyReport:
    """读取指定日期所在周记录，生成周报文本并保存到 dailies 表。"""

    start_date, end_date = week_range(date_text)
    progress_rows = _list_range_progress(conn, start_date, end_date)
    completed_todos = _list_range_completed_todos(conn, start_date, end_date)
    if not progress_rows and not completed_todos:
        raise ValueError(f"{start_date} 至 {end_date} 暂无可生成周报的 Progress 或已完成 Todo")

    raw_context = _build_raw_context(f"{start_date}..{end_date}", progress_rows, completed_todos)
    content = (
        _generate_llm_report(raw_context, llm_config)
        if _is_llm_enabled(llm_config)
        else _compose_report(f"{start_date} 至 {end_date} 周报", progress_rows, completed_todos, "本周", "一、本周完成")
    )
    cursor = conn.execute(
        """
        INSERT INTO dailies (date, content, raw_context, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (start_date, content, raw_context, now_text()),
    )
    return DailyReport(daily_id=int(cursor.lastrowid), date=start_date, content=content, raw_context=raw_context)


def _is_llm_enabled(llm_config: LlmConfig | None) -> bool:
    """判断是否具备调用 OpenAI 兼容接口的必要配置。"""

    return bool(llm_config and llm_config.base_url and llm_config.api_key and llm_config.model)


def _generate_llm_report(raw_context: str, llm_config: LlmConfig | None) -> str:
    """调用 OpenAI 兼容接口生成日报文本。"""

    assert llm_config is not None
    assert llm_config.base_url is not None
    assert llm_config.api_key is not None
    payload = {
        "model": llm_config.model,
        "messages": [
            {
                "role": "system",
                "content": "你是专业研发日报助理。只输出日报正文，不要解释生成过程。",
            },
            {
                "role": "user",
                "content": f"{PROMPT_INSTRUCTION}\n\n原始记录快照如下：\n{raw_context}",
            },
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    response = _request_chat_completion(llm_config.base_url, llm_config.api_key, payload)
    content = _extract_message_content(response)
    if not content:
        raise ValueError("大模型返回了空日报")
    return content


def _extract_message_content(response: dict[str, object]) -> str:
    """从 OpenAI 兼容响应里提取文本内容并校验结构。"""

    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("大模型接口响应格式错误")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ValueError("大模型接口响应格式错误")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise ValueError("大模型接口响应格式错误")
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("大模型接口响应格式错误")
    return content.strip()


def _request_chat_completion(base_url: str, api_key: str, payload: dict[str, object]) -> dict[str, object]:
    """发起 Chat Completions 请求并解析响应。"""

    url = f"{base_url.rstrip('/')}{CHAT_COMPLETIONS_PATH}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except error.URLError as exc:
        raise ValueError(f"大模型接口调用失败: {exc}") from exc
    parsed = json.loads(body)
    if not isinstance(parsed, dict) or not parsed.get("choices"):
        raise ValueError("大模型接口响应格式错误")
    return parsed


def _list_daily_progress(conn: Connection, day: str) -> list[Row]:
    """查询日报所需的当天 Progress 流水账。"""

    return list(
        conn.execute(
            """
            SELECT p.id, p.title, p.content, p.tag, p.source, p.created_at, pr.name AS project_name
            FROM progress p
            LEFT JOIN projects pr ON pr.id = p.project_id
            WHERE date(p.created_at) = ? AND p.source != 'todo_done'
            ORDER BY p.created_at ASC, p.id ASC
            """,
            (day,),
        )
    )


def _list_completed_todos(conn: Connection, day: str) -> list[Row]:
    """查询日报补充上下文所需的当天完成 Todo。"""

    return list(
        conn.execute(
            """
            SELECT t.id, t.title, t.content, t.tag, t.completed_at, pr.name AS project_name
            FROM todos t
            LEFT JOIN projects pr ON pr.id = t.project_id
            WHERE date(t.completed_at) = ?
            ORDER BY t.completed_at ASC, t.id ASC
            """,
            (day,),
        )
    )


def _list_range_progress(conn: Connection, start_date: str, end_date: str) -> list[Row]:
    """查询指定日期范围内的 Progress 流水账。"""

    return list(
        conn.execute(
            """
            SELECT p.id, p.title, p.content, p.tag, p.source, p.created_at, pr.name AS project_name
            FROM progress p
            LEFT JOIN projects pr ON pr.id = p.project_id
            WHERE date(p.created_at) BETWEEN ? AND ? AND p.source != 'todo_done'
            ORDER BY p.created_at ASC, p.id ASC
            """,
            (start_date, end_date),
        )
    )


def _list_range_completed_todos(conn: Connection, start_date: str, end_date: str) -> list[Row]:
    """查询指定日期范围内的已完成 Todo。"""

    return list(
        conn.execute(
            """
            SELECT t.id, t.title, t.content, t.tag, t.completed_at, pr.name AS project_name
            FROM todos t
            LEFT JOIN projects pr ON pr.id = t.project_id
            WHERE date(t.completed_at) BETWEEN ? AND ?
            ORDER BY t.completed_at ASC, t.id ASC
            """,
            (start_date, end_date),
        )
    )


def _build_raw_context(day: str, progress_rows: list[Row], completed_todos: list[Row]) -> str:
    """保存生成日报时使用的原始快照，方便后续追溯。"""

    snapshot = {
        "date": day,
        "prompt": PROMPT_INSTRUCTION,
        "progress": [_row_to_dict(row) for row in progress_rows],
        "completed_todos": [_row_to_dict(row) for row in completed_todos],
    }
    return json.dumps(snapshot, ensure_ascii=False, indent=2)


def _compose_report(
    title: str,
    progress_rows: list[Row],
    completed_todos: list[Row],
    period_label: str,
    progress_heading: str,
) -> str:
    """在未接入真实 LLM 前生成稳定、可汇报的日报文本。"""

    lines = [
        title,
        "",
        progress_heading,
    ]
    for index, row in enumerate(progress_rows, start=1):
        project = row["project_name"] or "未关联项目"
        lines.append(f"{index}. [{project}][{row['tag']}] {_format_title_content(row)}")

    if completed_todos:
        lines.extend(["", "二、完成 Todo"])
        for index, row in enumerate(completed_todos, start=1):
            project = row["project_name"] or "未关联项目"
            lines.append(f"{index}. [{project}][{row['tag']}] {_format_title_content(row)}")

    lines.extend(
        [
            "",
            "三、汇报摘要",
            _compose_summary(progress_rows, completed_todos, period_label),
        ]
    )
    return "\n".join(lines)


def _compose_summary(progress_rows: list[Row], completed_todos: list[Row], period_label: str) -> str:
    """按项目和标签聚合生成简短汇报摘要。"""

    project_names = sorted(
        {
            row["project_name"]
            for row in [*progress_rows, *completed_todos]
            if row["project_name"]
        }
    )
    tags = sorted({row["tag"] for row in [*progress_rows, *completed_todos]})
    project_text = "、".join(project_names) if project_names else "未关联项目"
    tag_text = "、".join(tags)
    return f"{period_label}围绕 {project_text} 推进了 {len(progress_rows)} 条工作进展，完成 {len(completed_todos)} 个 Todo，覆盖 {tag_text} 等类型。"


def _row_to_dict(row: Row) -> dict[str, object]:
    """将 SQLite Row 转成可序列化字典。"""

    return {key: row[key] for key in row.keys()}


def _format_title_content(row: Row) -> str:
    """把标题和可选详情合成为适合日报的单行文本。"""

    if row["content"]:
        return f"{row['title']}：{row['content']}"
    return str(row["title"])
