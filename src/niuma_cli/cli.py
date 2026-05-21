"""niuma 命令行入口。"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from sqlite3 import Row

from niuma_cli import __version__
from niuma_cli.app import create_app_context
from niuma_cli.interactive import choose_project_id, choose_tag
from niuma_cli.output import render_table
from niuma_cli.services import progress, projects, tags, todos


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""

    parser = argparse.ArgumentParser(
        prog="niuma",
        description="记录项目、Todo 和工作进展的本地 CLI。",
    )
    parser.add_argument("--version", action="version", version=f"niuma {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    project_parser = subparsers.add_parser("project", help="项目管理")
    project_subparsers = project_parser.add_subparsers(dest="project_command")
    project_create = project_subparsers.add_parser("create", help="创建项目")
    project_create.add_argument("name")
    project_subparsers.add_parser("list", help="列出项目")

    todo_parser = subparsers.add_parser("todo", help="Todo 管理")
    todo_subparsers = todo_parser.add_subparsers(dest="todo_command")
    todo_add = todo_subparsers.add_parser("add", help="创建 Todo")
    todo_add.add_argument("content")
    todo_add.add_argument("-p", "--project-id", type=int)
    todo_add.add_argument("-t", "--tag")
    todo_done = todo_subparsers.add_parser("done", help="完成 Todo")
    todo_done.add_argument("id", type=int)
    todo_list = todo_subparsers.add_parser("list", help="列出 Todo")
    todo_list.add_argument("date", nargs="?")

    progress_parser = subparsers.add_parser("progress", help="Progress 流水账")
    progress_subparsers = progress_parser.add_subparsers(dest="progress_command")
    progress_log = progress_subparsers.add_parser("log", help="记录工作进展")
    progress_log.add_argument("content")
    progress_log.add_argument("-p", "--project-id", type=int)
    progress_log.add_argument("-t", "--tag")
    progress_list = progress_subparsers.add_parser("list", help="列出工作进展")
    progress_list.add_argument("date", nargs="?")

    config_parser = subparsers.add_parser("config", help="配置管理")
    config_subparsers = config_parser.add_subparsers(dest="config_command")
    config_get = config_subparsers.add_parser("get", help="读取配置")
    config_get.add_argument("key")
    config_set = config_subparsers.add_parser("set", help="写入配置")
    config_set.add_argument("key")
    config_set.add_argument("value")
    config_subparsers.add_parser("reset", help="恢复默认配置")
    tags_parser = config_subparsers.add_parser("tags", help="标签配置")
    tags_subparsers = tags_parser.add_subparsers(dest="tags_command")
    tags_subparsers.add_parser("list", help="列出标签")
    tags_add = tags_subparsers.add_parser("add", help="新增标签")
    tags_add.add_argument("tag_name")
    tags_del = tags_subparsers.add_parser("del", help="删除标签")
    tags_del.add_argument("tag_name")
    tags_rename = tags_subparsers.add_parser("rename", help="重命名标签")
    tags_rename.add_argument("old_name")
    tags_rename.add_argument("new_name")

    subparsers.add_parser("status", help="查看当前状态")
    return parser


def main(argv: list[str] | None = None) -> int:
    """执行 CLI 命令并返回进程退出码。"""

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    try:
        context = create_app_context(initialize_database=_requires_database(args))
        return _dispatch(args, context)
    except (ValueError, KeyError, OSError, sqlite3.Error) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


def _dispatch(args: argparse.Namespace, context) -> int:
    """路由到具体命令处理器。"""

    if args.command == "project":
        return _handle_project(args, context)
    if args.command == "todo":
        return _handle_todo(args, context)
    if args.command == "progress":
        return _handle_progress(args, context)
    if args.command == "config":
        return _handle_config(args, context)
    if args.command == "status":
        return _handle_status(context)
    raise ValueError(f"不支持的命令: {args.command}")


def _requires_database(args: argparse.Namespace) -> bool:
    """判断当前命令是否需要可连接数据库。"""

    return not (args.command == "config" and args.config_command in {"get", "set", "reset"})


def _handle_project(args: argparse.Namespace, context) -> int:
    """处理项目命令。"""

    with context.database.connect() as conn:
        if args.project_command == "create":
            project_id = projects.create_project(conn, args.name)
            print(f"项目已创建: #{project_id} {args.name}")
            return 0
        if args.project_command == "list":
            rows = projects.list_projects(conn)
            print(_render_rows(["ID", "项目", "创建时间"], ((row["id"], row["name"], row["created_at"]) for row in rows)))
            return 0
    raise ValueError("请指定 project 子命令")


def _handle_todo(args: argparse.Namespace, context) -> int:
    """处理 Todo 命令。"""

    with context.database.connect() as conn:
        if args.todo_command == "add":
            tag = tags.validate_tag(context.config_store, choose_tag(tags.list_tags(context.config_store), args.tag))
            project_id = choose_project_id(projects.list_projects(conn), args.project_id)
            todo_id = todos.create_todo(conn, args.content, tag, project_id)
            print(f"Todo 已创建: #{todo_id}")
            return 0
        if args.todo_command == "done":
            progress_id = todos.complete_todo(conn, args.id)
            print(f"Todo 已完成，并生成 Progress: #{progress_id}")
            return 0
        if args.todo_command == "list":
            grouped = todos.list_todos(conn, args.date)
            print(_render_todo_sections(grouped))
            return 0
    raise ValueError("请指定 todo 子命令")


def _handle_progress(args: argparse.Namespace, context) -> int:
    """处理 Progress 命令。"""

    with context.database.connect() as conn:
        if args.progress_command == "log":
            tag = tags.validate_tag(context.config_store, choose_tag(tags.list_tags(context.config_store), args.tag))
            project_id = choose_project_id(projects.list_projects(conn), args.project_id)
            progress_id = progress.create_progress(conn, args.content, tag, project_id)
            print(f"Progress 已记录: #{progress_id}")
            return 0
        if args.progress_command == "list":
            rows = progress.list_progress(conn, args.date)
            print(
                _render_rows(
                    ["ID", "时间", "项目", "标签", "来源", "内容"],
                    (
                        (
                            row["id"],
                            row["created_at"],
                            row["project_name"] or "-",
                            row["tag"],
                            row["source"],
                            row["content"],
                        )
                        for row in rows
                    ),
                )
            )
            return 0
    raise ValueError("请指定 progress 子命令")


def _handle_config(args: argparse.Namespace, context) -> int:
    """处理配置命令。"""

    if args.config_command == "get":
        print(context.config_store.get(args.key))
        return 0
    if args.config_command == "set":
        if args.key != "db.path":
            raise KeyError(f"不支持的配置项: {args.key}")
        config = context.config_store.set_db_path(args.value)
        print(f"db.path 已更新: {config.db_path}")
        return 0
    if args.config_command == "reset":
        config = context.config_store.reset()
        print(f"配置已重置，db.path: {config.db_path}")
        return 0
    if args.config_command == "tags":
        with context.database.connect() as conn:
            return _handle_tags(args, context, conn)
    raise ValueError("请指定 config 子命令")


def _handle_tags(args: argparse.Namespace, context, conn) -> int:
    """处理标签配置命令。"""

    if args.tags_command == "list":
        print("\n".join(tags.list_tags(context.config_store)))
        return 0
    if args.tags_command == "add":
        updated = tags.add_tag(context.config_store, args.tag_name)
        print(f"标签已新增: {args.tag_name}")
        print("\n".join(updated))
        return 0
    if args.tags_command == "del":
        updated = tags.delete_tag(conn, context.config_store, args.tag_name)
        print(f"标签已删除: {args.tag_name}")
        print("\n".join(updated))
        return 0
    if args.tags_command == "rename":
        updated = tags.rename_tag(conn, context.config_store, args.old_name, args.new_name)
        print(f"标签已重命名: {args.old_name} -> {args.new_name}")
        print("\n".join(updated))
        return 0
    raise ValueError("请指定 config tags 子命令")


def _handle_status(context) -> int:
    """输出数据库和今日任务状态。"""

    with context.database.connect() as conn:
        completed, pending = todos.count_today(conn)
    print(
        render_table(
            ["项目", "值"],
            [
                ("数据库路径", context.database.path),
                ("数据库状态", "可连接"),
                ("今日完成 Todo", completed),
                ("当前未完成 Todo", pending),
            ],
        )
    )
    return 0


def _render_todo_sections(grouped: dict[str, list[Row]]) -> str:
    """渲染 Todo 三个核心分区。"""

    names = {
        "pending": "未完成 Todo",
        "created": "当天新建 Todo",
        "completed": "当天完成 Todo",
    }
    sections: list[str] = []
    for key, rows in grouped.items():
        sections.append(names[key])
        sections.append(
            _render_rows(
                ["ID", "项目", "标签", "状态", "内容"],
                ((row["id"], row["project_name"] or "-", row["tag"], row["status"], row["content"]) for row in rows),
            )
        )
    return "\n\n".join(sections)


def _render_rows(headers: list[str], rows) -> str:
    """渲染行数据；空结果给出清晰提示。"""

    materialized = list(rows)
    if not materialized:
        return "暂无数据"
    return render_table(headers, materialized)


if __name__ == "__main__":
    raise SystemExit(main())
