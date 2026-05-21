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
```
