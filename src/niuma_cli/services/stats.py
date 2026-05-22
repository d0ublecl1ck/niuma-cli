"""统计与复盘业务。"""

from __future__ import annotations

from dataclasses import dataclass
from sqlite3 import Connection, Row

from niuma_cli.time_utils import month_range, week_range


@dataclass(frozen=True)
class StatsReport:
    """表达指定周期内的统计结果。"""

    period: str
    start_date: str
    end_date: str
    tag_rows: list[Row]
    project_rows: list[Row]


def build_stats(conn: Connection, period: str) -> StatsReport:
    """按周或月聚合任务和项目投入。"""

    start_date, end_date = _period_range(period)
    tag_rows = list(
        conn.execute(
            """
            SELECT tag, COUNT(*) AS count
            FROM todos
            WHERE status = 'done' AND date(completed_at) BETWEEN ? AND ?
            GROUP BY tag
            ORDER BY count DESC, tag ASC
            """,
            (start_date, end_date),
        )
    )
    project_rows = list(
        conn.execute(
            """
            SELECT COALESCE(pr.name, '未关联项目') AS project_name, COUNT(*) AS count
            FROM progress p
            LEFT JOIN projects pr ON pr.id = p.project_id
            WHERE date(p.happened_at) BETWEEN ? AND ?
            GROUP BY COALESCE(pr.name, '未关联项目')
            ORDER BY count DESC, project_name ASC
            """,
            (start_date, end_date),
        )
    )
    return StatsReport(period=period, start_date=start_date, end_date=end_date, tag_rows=tag_rows, project_rows=project_rows)


def _period_range(period: str) -> tuple[str, str]:
    """解析统计周期。"""

    if period == "week":
        return week_range()
    if period == "month":
        return month_range()
    raise ValueError("统计周期只支持 week 或 month")
