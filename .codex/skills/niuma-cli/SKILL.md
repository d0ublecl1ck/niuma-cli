---
name: niuma-cli
description: Develop, debug, test, and document the niuma-cli local Python command-line tool for developer work logs, projects, todos, progress records, focus/chill sessions, tags, config recovery, stats, daily or weekly reports, and OpenAI-compatible LLM report generation. Use when working in or discussing the niuma-cli repository, commands, SQLite schema, local config, tests, docs, packaging, or user-facing CLI behavior.
---

# Niuma CLI

Use this skill to work on the `niuma-cli` repository without rediscovering its command model, data boundaries, and verification paths.

## Start Here

- Treat the project as a Python 3.11+ CLI managed with uv.
- Run `~/.codex/detect-tech-stack.sh <project_dir>` before development decisions.
- Use `$dev-skill` and `$python-dev` for implementation work.
- Read `references/project-guide.md` before making changes that affect command behavior, data persistence, config, reporting, or tests.
- Prefer `uv run pytest` for the full validation path and targeted `uv run pytest tests/test_cli.py -k '<pattern>'` while iterating.

## Development Workflow

1. Inspect the affected command in `src/niuma_cli/cli.py` and the backing service in `src/niuma_cli/services/`.
2. Model the smallest end-to-end CLI path first: parser argument, dispatcher branch, service behavior, persisted state, and terminal output.
3. Keep persistent behavior isolated behind `ConfigStore` and `Database`; do not let command handlers manually assemble config or SQLite paths.
4. Use `NIUMA_HOME=<tmpdir>` for manual smoke tests so local user data under `~/.niuma` is not touched.
5. Add or update CLI-level tests in `tests/test_cli.py` for user-visible behavior, persistence, config recovery, tag migration, focus/chill sessions, stats, or report generation.
6. Update `README.md` when commands, examples, configuration keys, or install/verification steps change.
7. Update `docs/dev/` and the project `AGENTS.md` index when fixing a confirmed regression with reusable prevention value.

## Command Model

- `project create|rename|list` manages projects.
- `todo add|modify|done|list|show|focus|focus-log|stop` manages todos and focus records.
- `progress log|new|modify|list|show` manages progress records.
- `search <query>` performs fuzzy search across projects, todos, progress records, dailies, and tags; use `--entity <entity>` to narrow scope.
- `todo add <title>`, `progress log <title>`, and `progress new <title>` require a concise title and accept optional `--content` details.
- `progress log` and `progress new` accept `--data`, `--date`, or `--at` business time for backfill or prefill records; progress lists, reports, and stats use business time instead of creation audit time.
- `todo modify` and `progress modify` update title, content, tag, project association, and Progress business time when `--title`, `--content`, `--tag`, `--project-id`, or `--data` is provided.
- `todo list` and `progress list` show content summaries capped at 20 characters by default; use `--content-limit <n>` to adjust or `--title-only` to hide content.
- Use `todo show <id>` or `progress show <id>` when full content is needed.
- Split Todo and Progress records atomically by independently understandable work outcome; avoid bundling multiple unrelated changes, fixes, docs, and verification items into one broad record.
- Before creating Todo or Progress records, run or inspect `project list` when the target project is not certain, then prefer passing `--project-id` so records do not fall into the unassociated project bucket.
- Strongly recommend writing `--content` for Todo and Progress entries; use `title` for the short outcome-oriented summary and `content` for important context, scope, blockers, evidence, or follow-up details.
- Prefer concise user-value titles over implementation dumps: `完成大宗原材料可比降低率业务口径开发` is better than a long PR-style implementation summary with every file, test, version, and compatibility detail.
- `project rename` updates the project name in place, so related Todo and Progress list output shows the new project name through joins.

## Boundaries

- Preserve Chinese user-facing CLI output and test assertions unless the task explicitly changes copy.
- Keep comments and docstrings in Chinese when changing code in this repository.
- Do not initialize the database for pure config recovery commands such as `config get`, `config set`, or `config reset`.
- Mask `llm.api_key` in terminal output and keep config files private when storing secrets.
- Block deletion of the last tag and block deletion of tags that are referenced by historical records.
- Migrate todos, progress records, and active sessions when renaming tags.
- Avoid live external LLM calls in tests; monkeypatch the request helper instead.

## Useful Commands

```bash
uv sync
uv run pytest
uv run pytest tests/test_cli.py -k 'config or tag'
NIUMA_HOME="$(mktemp -d)" uv run niuma status
NIUMA_HOME="$(mktemp -d)" uv run niuma project create 电商系统
NIUMA_HOME="$(mktemp -d)" uv run niuma project rename 1 支付系统
NIUMA_HOME="$(mktemp -d)" uv run niuma todo add "修复登录页验证码报错" --content "复现路径、影响范围和下一步处理计划" -p 1 -t Bug
NIUMA_HOME="$(mktemp -d)" uv run niuma todo modify 1 --title "修复登录页验证码重试报错" --content "已确认错误恢复路径" -p 1 -t Bug
NIUMA_HOME="$(mktemp -d)" uv run niuma todo list --title-only
NIUMA_HOME="$(mktemp -d)" uv run niuma todo show 1
NIUMA_HOME="$(mktemp -d)" uv run niuma progress log "完成支付接口联调" --content "覆盖下单、回调和异常重试链路" -p 1 -t Feature
NIUMA_HOME="$(mktemp -d)" uv run niuma progress new "补录支付接口联调" --data "2026-05-21 23:30" --content "覆盖下单、回调和异常重试链路" -p 1 -t Feature
NIUMA_HOME="$(mktemp -d)" uv run niuma progress modify 1 --title "完成支付接口回归" --content "已补齐回调失败场景" -p 1 -t Feature
NIUMA_HOME="$(mktemp -d)" uv run niuma progress modify 1 --data "2026-05-22 10:30"
NIUMA_HOME="$(mktemp -d)" uv run niuma progress list --content-limit 50
NIUMA_HOME="$(mktemp -d)" uv run niuma progress show 1
NIUMA_HOME="$(mktemp -d)" uv run niuma search "支付" --entity progress
```
