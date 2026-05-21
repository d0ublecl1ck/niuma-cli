from __future__ import annotations

from pathlib import Path
import json

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


def test_config_reset_recovers_from_bad_database_path(tmp_path: Path, monkeypatch) -> None:
    """验证数据库路径配坏后仍可通过 config reset 恢复。"""

    monkeypatch.setenv("NIUMA_HOME", str(tmp_path))
    bad_parent = tmp_path / "blocked-parent"
    bad_parent.write_text("not a directory", encoding="utf-8")

    assert main(["config", "set", "db.path", str(bad_parent / "niuma.db")]) == 0
    assert main(["status"]) == 1
    assert main(["config", "reset"]) == 0
    assert main(["status"]) == 0


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
