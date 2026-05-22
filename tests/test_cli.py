from __future__ import annotations

from pathlib import Path
import json
import sqlite3

from niuma_cli.cli import main


def test_v1_project_todo_progress_flow(tmp_path: Path, monkeypatch) -> None:
    """验证 V1.0 项目、Todo、完成物化和查询闭环。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["project", "create", "电商系统"]) == 0
    assert main(["todo", "add", "修复登录页验证码报错", "-p", "1", "-t", "Bug"]) == 0
    assert main(["todo", "done", "1"]) == 0
    assert main(["progress", "log", "和前端联调支付接口", "-p", "1", "-t", "Feature"]) == 0
    assert main(["todo", "list"]) == 0
    assert main(["progress", "list"]) == 0

    assert (tmp_path / "niuma.db").exists()


def test_tag_delete_is_blocked_when_referenced(tmp_path: Path, monkeypatch) -> None:
    """验证已被引用的标签不能直接删除。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["todo", "add", "补充单元测试", "-t", "Feature"]) == 0
    assert main(["config", "tags", "del", "Feature"]) == 1


def test_tag_rename_migrates_history(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证标签重命名同步迁移 Todo 和 Progress 历史数据。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["todo", "add", "优化首页加载速度", "-t", "Feature"]) == 0
    assert main(["progress", "log", "压缩静态资源", "-t", "Feature"]) == 0
    assert main(["config", "tags", "rename", "Feature", "Frontend"]) == 0
    assert main(["todo", "list"]) == 0
    assert main(["progress", "list"]) == 0

    output = capsys.readouterr().out
    assert "Frontend" in output
    assert "Feature" not in output.split("标签已重命名: Feature -> Frontend", maxsplit=1)[-1]


def test_project_rename_updates_project_name_in_related_lists(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证项目重命名后，关联 Todo 和 Progress 展示新项目名。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["project", "create", "旧项目"]) == 0
    assert main(["todo", "add", "接入支付回调", "-p", "1", "-t", "Feature"]) == 0
    assert main(["progress", "log", "完成支付回调联调", "-p", "1", "-t", "Feature"]) == 0
    assert main(["project", "rename", "1", "新项目"]) == 0
    assert main(["todo", "list"]) == 0
    assert main(["progress", "list"]) == 0

    output = capsys.readouterr().out
    assert "项目已重命名: #1 旧项目 -> 新项目" in output
    assert "新项目" in output
    assert "旧项目" not in output.split("项目已重命名: #1 旧项目 -> 新项目", maxsplit=1)[-1]


def test_todo_modify_updates_title_content_tag_and_project(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证 Todo modify 可以更新标题、内容、标签和项目关联。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["project", "create", "旧项目"]) == 0
    assert main(["project", "create", "新项目"]) == 0
    assert main(["todo", "add", "旧 Todo", "--content", "旧详情", "-p", "1", "-t", "Feature"]) == 0
    assert main(["todo", "modify", "1", "--title", "新 Todo", "--content", "新详情", "--tag", "Bug", "--project-id", "2"]) == 0
    assert main(["todo", "list"]) == 0

    output = capsys.readouterr().out
    assert "Todo 已更新: #1" in output
    assert "新 Todo" in output
    assert "新详情" in output
    assert "Bug" in output
    assert "新项目" in output
    assert "旧 Todo" not in output.split("Todo 已更新: #1", maxsplit=1)[-1]
    assert "旧详情" not in output.split("Todo 已更新: #1", maxsplit=1)[-1]


def test_progress_modify_updates_title_content_tag_and_project(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证 Progress modify 可以更新标题、内容、标签和项目关联。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["project", "create", "旧项目"]) == 0
    assert main(["project", "create", "新项目"]) == 0
    assert main(["progress", "log", "旧进展", "--content", "旧详情", "-p", "1", "-t", "Feature"]) == 0
    assert main(["progress", "modify", "1", "--title", "新进展", "--content", "新详情", "--tag", "Bug", "--project-id", "2"]) == 0
    assert main(["progress", "list"]) == 0

    output = capsys.readouterr().out
    assert "Progress 已更新: #1" in output
    assert "新进展" in output
    assert "新详情" in output
    assert "Bug" in output
    assert "新项目" in output
    assert "旧进展" not in output.split("Progress 已更新: #1", maxsplit=1)[-1]
    assert "旧详情" not in output.split("Progress 已更新: #1", maxsplit=1)[-1]


def test_todo_list_truncates_content_and_can_show_title_only(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证 Todo 列表默认截断详情，并支持仅展示标题。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    long_content = "一二三四五六七八九十一二三四五六七八九十完整详情"
    assert main(["todo", "add", "长内容 Todo", "--content", long_content, "-t", "Feature"]) == 0
    assert main(["todo", "list"]) == 0

    output = capsys.readouterr().out
    assert "一二三四五六七八九十一二三四五六七八九十..." in output
    assert long_content not in output.split("Todo 已创建: #1", maxsplit=1)[-1]

    assert main(["todo", "list", "--title-only"]) == 0
    title_only_output = capsys.readouterr().out
    assert "长内容 Todo" in title_only_output
    assert "完整详情" not in title_only_output
    assert long_content not in title_only_output


def test_progress_list_content_limit_and_show_full_content(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证 Progress 列表可限制详情字数，show 可查看完整详情。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    content = "这是超过五个字的完整进展详情"
    assert main(["progress", "log", "长内容进展", "--content", content, "-t", "Feature"]) == 0
    assert main(["progress", "list", "--content-limit", "5"]) == 0

    output = capsys.readouterr().out
    assert "这是超过五..." in output
    assert content not in output.split("Progress 已记录: #1", maxsplit=1)[-1]

    assert main(["progress", "show", "1"]) == 0
    show_output = capsys.readouterr().out
    assert "长内容进展" in show_output
    assert content in show_output


def test_todo_show_returns_full_content(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证 Todo show 可查看完整标题和详情。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    content = "Todo 的完整内容不会在详情命令里被截断"
    assert main(["todo", "add", "查看详情 Todo", "--content", content, "-t", "Feature"]) == 0
    assert main(["todo", "show", "1"]) == 0

    output = capsys.readouterr().out
    assert "查看详情 Todo" in output
    assert content in output


def test_search_finds_all_supported_entities(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证 search 默认能跨 Project、Todo、Progress、Daily 和 Tag 搜索。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["config", "tags", "add", "SearchTag"]) == 0
    assert main(["project", "create", "搜索项目"]) == 0
    assert main(["todo", "add", "搜索 Todo", "--content", "待办详情", "-p", "1", "-t", "SearchTag"]) == 0
    assert main(["progress", "log", "搜索 Progress", "--content", "进展详情", "-p", "1", "-t", "SearchTag"]) == 0
    assert main(["daily", "generate"]) == 0
    assert main(["search", "搜索"]) == 0

    output = capsys.readouterr().out
    assert "project" in output
    assert "todo" in output
    assert "progress" in output
    assert "daily" in output
    assert "搜索项目" in output
    assert "搜索 Todo" in output
    assert "搜索 Progress" in output

    assert main(["search", "SearchTag"]) == 0
    tag_output = capsys.readouterr().out
    assert "tag" in tag_output
    assert "SearchTag" in tag_output


def test_search_can_filter_entity_and_truncate_content(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证 search 支持实体限定和内容摘要长度控制。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["todo", "add", "搜索目标", "--content", "这是一段很长的搜索详情", "-t", "Feature"]) == 0
    assert main(["progress", "log", "搜索目标进展", "--content", "不应该出现在 Todo 限定结果", "-t", "Feature"]) == 0
    assert main(["search", "搜索", "--entity", "todo", "--content-limit", "4"]) == 0

    output = capsys.readouterr().out
    assert "todo" in output
    assert "搜索目标" in output
    assert "这是一段..." in output
    assert "progress" not in output
    assert "不应该出现在 Todo 限定结果" not in output


def test_search_is_case_insensitive_for_english_content(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证英文搜索大小写不敏感。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["progress", "log", "Fix Login Flow", "--content", "Cover Retry Path", "-t", "Feature"]) == 0
    assert main(["search", "login", "--entity", "progress"]) == 0

    output = capsys.readouterr().out
    assert "Fix Login Flow" in output


def test_search_rejects_empty_query(tmp_path: Path, monkeypatch) -> None:
    """验证 search 拒绝空白关键词。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["search", "   "]) == 1


def test_modify_requires_at_least_one_field(tmp_path: Path, monkeypatch) -> None:
    """验证 modify 必须提供至少一个可更新字段，避免无意义写入。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["todo", "add", "保留原 Todo", "-t", "Feature"]) == 0
    assert main(["progress", "log", "保留原进展", "-t", "Feature"]) == 0
    assert main(["todo", "modify", "1"]) == 1
    assert main(["progress", "modify", "1"]) == 1


def test_existing_todo_and_progress_content_migrates_to_title(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证旧库里的 content 字段会迁移为 title，content 详情保持为空。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))
    db_path = tmp_path / "niuma.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                content TEXT NOT NULL,
                tag TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('pending', 'done')),
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE TABLE progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                todo_id INTEGER REFERENCES todos(id) ON DELETE SET NULL,
                content TEXT NOT NULL,
                tag TEXT NOT NULL,
                source TEXT NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO todos (content, tag, status, created_at, completed_at) VALUES (?, ?, 'pending', ?, NULL)",
            ("旧 Todo 内容", "Feature", "2026-05-22 09:00:00"),
        )
        conn.execute(
            "INSERT INTO progress (content, tag, source, created_at) VALUES (?, ?, 'manual', ?)",
            ("旧 Progress 内容", "Feature", "2026-05-22 09:10:00"),
        )

    assert main(["todo", "list", "2026-05-22"]) == 0
    assert main(["progress", "list", "2026-05-22"]) == 0

    output = capsys.readouterr().out
    assert "旧 Todo 内容" in output
    assert "旧 Progress 内容" in output
    with sqlite3.connect(db_path) as conn:
        todo_row = conn.execute("SELECT title, content FROM todos WHERE id = 1").fetchone()
        progress_row = conn.execute("SELECT title, content FROM progress WHERE id = 1").fetchone()
    assert todo_row == ("旧 Todo 内容", None)
    assert progress_row == ("旧 Progress 内容", None)


def test_config_reset_recovers_from_bad_database_path(tmp_path: Path, monkeypatch) -> None:
    """验证数据库路径配坏后仍可通过 config reset 恢复。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))
    bad_parent = tmp_path / "blocked-parent"
    bad_parent.write_text("not a directory", encoding="utf-8")

    assert main(["config", "set", "db.path", str(bad_parent / "niuma.db")]) == 0
    assert main(["status"]) == 1
    assert main(["config", "reset"]) == 0
    assert main(["status"]) == 0


def test_config_set_llm_api_key_masks_output(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证写入大模型密钥时不会把明文密钥输出到终端。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["config", "set", "llm.api_key", "secret-value"]) == 0

    output = capsys.readouterr().out
    assert "secret-value" not in output
    assert "llm.api_key 已更新: ***" in output


def test_config_get_llm_api_key_masks_output(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证读取大模型密钥时不会把明文密钥输出到终端。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["config", "set", "llm.api_key", "secret-value"]) == 0
    capsys.readouterr()
    assert main(["config", "get", "llm.api_key"]) == 0

    output = capsys.readouterr().out
    assert output.strip() == "***"


def test_config_file_is_private_when_storing_llm_api_key(tmp_path: Path, monkeypatch) -> None:
    """验证保存大模型密钥时配置文件权限为 0600。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["config", "set", "llm.api_key", "secret-value"]) == 0

    assert oct((tmp_path / "config.json").stat().st_mode & 0o777) == "0o600"


def test_deleting_last_tag_is_blocked(tmp_path: Path, monkeypatch) -> None:
    """验证删除最后一个标签会失败，避免下次读取复活默认标签。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))
    config_path = tmp_path / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps({"db": {"path": str(tmp_path / "niuma.db")}, "tags": ["Only"]}, ensure_ascii=False),
        encoding="utf-8",
    )

    assert main(["config", "tags", "del", "Only"]) == 1
    assert main(["config", "tags", "list"]) == 0


def test_daily_generate_persists_report_and_raw_context(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证日报生成会读取当天记录并持久化原始快照。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["project", "create", "电商系统"]) == 0
    assert main(["todo", "add", "修复登录页验证码报错", "-p", "1", "-t", "Bug"]) == 0
    assert main(["todo", "done", "1"]) == 0
    assert main(["progress", "log", "和前端联调支付接口", "-p", "1", "-t", "Feature"]) == 0
    assert main(["daily", "generate"]) == 0

    output = capsys.readouterr().out
    assert "日报已保存" in output
    assert "汇报摘要" in output

    with sqlite3.connect(tmp_path / "niuma.db") as conn:
        row = conn.execute("SELECT date, content, raw_context FROM dailies").fetchone()

    assert row is not None
    assert "修复登录页验证码报错" in row[1]
    raw_context = json.loads(row[2])
    assert raw_context["progress"]
    assert raw_context["completed_todos"]


def test_daily_generate_reports_empty_day(tmp_path: Path, monkeypatch) -> None:
    """验证无记录时日报生成给出明确失败提示。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["daily", "generate"]) == 1


def test_daily_generate_uses_llm_when_configured(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证配置大模型后日报生成优先使用接口返回内容。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    def fake_request_chat_completion(base_url: str, api_key: str, payload: dict[str, object]) -> dict[str, object]:
        """模拟 OpenAI 兼容接口，避免单元测试依赖外部网络。"""

        assert base_url == "http://llm.test"
        assert api_key == "test-key"
        assert payload["model"] == "test-model"
        return {"choices": [{"message": {"content": "AI 生成日报正文"}}]}

    monkeypatch.setattr("niuma_cli.services.dailies._request_chat_completion", fake_request_chat_completion)

    assert main(["config", "set", "llm.base_url", "http://llm.test"]) == 0
    assert main(["config", "set", "llm.api_key", "test-key"]) == 0
    assert main(["config", "set", "llm.model", "test-model"]) == 0
    assert main(["progress", "log", "完成日报大模型接入", "-t", "Feature"]) == 0
    assert main(["daily", "generate"]) == 0

    output = capsys.readouterr().out
    assert "AI 生成日报正文" in output


def test_daily_generate_rejects_non_string_llm_content(tmp_path: Path, monkeypatch) -> None:
    """验证大模型 content 非字符串时返回可控错误。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    def fake_request_chat_completion(base_url: str, api_key: str, payload: dict[str, object]) -> dict[str, object]:
        """模拟异常 OpenAI 兼容响应。"""

        return {"choices": [{"message": {"content": None}}]}

    monkeypatch.setattr("niuma_cli.services.dailies._request_chat_completion", fake_request_chat_completion)

    assert main(["config", "set", "llm.base_url", "http://llm.test"]) == 0
    assert main(["config", "set", "llm.api_key", "test-key"]) == 0
    assert main(["progress", "log", "触发异常响应", "-t", "Feature"]) == 0
    assert main(["daily", "generate"]) == 1


def test_daily_generate_deduplicates_todo_done_progress(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证日报不会重复统计 todo done 自动生成的 Progress 和已完成 Todo。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["todo", "add", "避免日报重复", "-t", "Feature"]) == 0
    assert main(["todo", "done", "1"]) == 0
    assert main(["daily", "generate"]) == 0

    output = capsys.readouterr().out
    assert "【已完成 Todo】避免日报重复" not in output
    assert output.count("避免日报重复") == 1
    assert "推进了 0 条工作进展，完成 1 个 Todo" in output


def test_focus_stop_creates_progress(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证专注计时结束后会自动生成 Progress。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["project", "create", "电商系统"]) == 0
    assert main(["todo", "add", "实现专注计时", "-p", "1", "-t", "Feature"]) == 0
    assert main(["todo", "focus", "1"]) == 0
    assert main(["todo", "stop"]) == 0
    assert main(["progress", "list"]) == 0

    output = capsys.readouterr().out
    assert "专注已结束" in output
    assert "【专注】耗时" in output
    assert "focus" in output


def test_tag_rename_migrates_active_focus_session(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证进行中的专注会话也会随标签重命名迁移。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["todo", "add", "迁移进行中标签", "-t", "Feature"]) == 0
    assert main(["todo", "focus", "1"]) == 0
    assert main(["config", "tags", "rename", "Feature", "Focused"]) == 0
    assert main(["todo", "stop"]) == 0
    assert main(["progress", "list"]) == 0

    output = capsys.readouterr().out
    assert "Focused" in output


def test_focus_log_accepts_time_range(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证可以用开始和结束时间补录专注。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["project", "create", "电商系统"]) == 0
    assert main(["todo", "add", "补录番茄钟", "-p", "1", "-t", "Feature"]) == 0
    assert main(["todo", "focus-log", "1", "--from", "09:00", "--to", "11:00"]) == 0
    assert main(["progress", "list"]) == 0

    output = capsys.readouterr().out
    assert "专注已补录，耗时 120 分钟" in output
    assert "【专注补录】耗时 120 分钟" in output


def test_focus_log_accepts_duration(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证可以用具体时长补录专注。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["todo", "add", "补录两小时专注", "-t", "Feature"]) == 0
    assert main(["todo", "focus-log", "1", "--duration", "2小时"]) == 0
    assert main(["progress", "list"]) == 0

    output = capsys.readouterr().out
    assert "专注已补录，耗时 120 分钟" in output
    assert "【专注补录】耗时 120 分钟" in output


def test_focus_log_accepts_chinese_compound_duration(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证中文复合数字时长不会被逐字替换成错误分钟数。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["todo", "add", "补录十二分钟专注", "-t", "Feature"]) == 0
    assert main(["todo", "focus-log", "1", "--duration", "十二分钟"]) == 0
    assert main(["todo", "focus-log", "1", "--duration", "二十分钟"]) == 0
    assert main(["progress", "list"]) == 0

    output = capsys.readouterr().out
    assert "耗时 12 分钟" in output
    assert "耗时 20 分钟" in output
    assert "耗时 102 分钟" not in output
    assert "耗时 210 分钟" not in output


def test_focus_log_requires_valid_time_input(tmp_path: Path, monkeypatch) -> None:
    """验证补录专注必须提供合法时间段或时长。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["todo", "add", "校验补录参数", "-t", "Feature"]) == 0
    assert main(["todo", "focus-log", "1", "--from", "11:00", "--to", "09:00"]) == 1
    assert main(["todo", "focus-log", "1"]) == 1


def test_chill_end_creates_hidden_progress(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证 Chill 结束后会自动生成隐藏标签 Progress。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["chill", "start", "等待上游环境配置"]) == 0
    assert main(["chill", "end"]) == 0
    assert main(["progress", "list"]) == 0

    output = capsys.readouterr().out
    assert "Chill 已结束" in output
    assert "__chill__" in output
    assert "chill" in output


def test_only_one_active_session_is_allowed(tmp_path: Path, monkeypatch) -> None:
    """验证同一时间只允许一个进行中的活动会话。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["chill", "start", "等待接口联调"]) == 0
    assert main(["chill", "start", "重复开始"]) == 1


def test_stats_week_and_weekly_report(tmp_path: Path, monkeypatch, capsys) -> None:
    """验证周统计和周报生成覆盖 V2 复盘入口。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))

    assert main(["project", "create", "电商系统"]) == 0
    assert main(["todo", "add", "修复支付回调", "-p", "1", "-t", "Bug"]) == 0
    assert main(["todo", "done", "1"]) == 0
    assert main(["progress", "log", "补充周报聚合能力", "-p", "1", "-t", "Feature"]) == 0
    assert main(["stats", "week"]) == 0
    assert main(["daily", "generate", "--week"]) == 0

    output = capsys.readouterr().out
    assert "按标签完成 Todo" in output
    assert "Bug" in output
    assert "周报" in output
    assert "一、本周完成" in output
    assert "周报已保存" in output
    assert "日报已保存" not in output
