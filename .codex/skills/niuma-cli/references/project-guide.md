# Niuma CLI Project Guide

## Architecture

- `src/niuma_cli/cli.py` owns argparse setup, command dispatch, terminal output, and exit-code conversion.
- `src/niuma_cli/app.py` builds `AppContext` from `ConfigStore` and `Database`.
- `src/niuma_cli/config.py` owns `NIUMA_HOME`, `~/.niuma/config.json`, default tags, LLM config, atomic config writes, and config permissions.
- `src/niuma_cli/db.py` owns SQLite schema creation, connection lifecycle, transactions, and foreign key enforcement.
- `src/niuma_cli/services/` owns domain operations for projects, todos, progress, activity sessions, tags, stats, and daily/weekly reports.
- `tests/test_cli.py` is the primary behavioral regression suite and exercises commands through `main(...)`.

## Command Model

- `project create|list` manages projects.
- `todo add|done|list|focus|focus-log|stop` manages todos and focus records.
- `progress log|list` manages progress records.
- `daily generate [--week]` creates daily or weekly reports and persists raw context.
- `chill start|end` tracks waiting or blocked time and materializes hidden progress.
- `stats week|month` summarizes work.
- `config get|set|reset|tags ...` manages local JSON config and tags.
- `status` reports current state.

## Data And Config Rules

- Default runtime data lives in `~/.niuma/niuma.db`; tests and smoke commands should set `NIUMA_HOME`.
- Config keys currently include `db.path`, `llm.base_url`, `llm.api_key`, and `llm.model`.
- LLM environment variables `NIUMA_LLM_BASE_URL`, `NIUMA_LLM_API_KEY`, and `NIUMA_LLM_MODEL` override stored config.
- `config reset` must work even after `db.path` points to an unusable path.
- Treat config JSON as user data: preserve unrelated keys where practical and avoid overwriting corrupted content silently.
- Use SQLite transactions through `Database.connect()` for mutations.

## Verification Patterns

- For most changes, run `uv run pytest`.
- For focused iteration, run `uv run pytest tests/test_cli.py -k '<topic>'`.
- For manual command smoke tests, use a temporary home:

```bash
tmp_home="$(mktemp -d)"
NIUMA_HOME="$tmp_home" uv run niuma project create 电商系统
NIUMA_HOME="$tmp_home" uv run niuma todo add "修复登录页验证码报错" -p 1 -t Bug
NIUMA_HOME="$tmp_home" uv run niuma todo done 1
NIUMA_HOME="$tmp_home" uv run niuma daily generate
```

## Regression Notes

- See the repository `docs/dev/config-recovery-and-tags.md` before changing config recovery, tag deletion, tag defaults, or tag migration behavior.
- When a bug fix exposes a durable prevention rule, add a concise note under `docs/dev/` and index it from the project `AGENTS.md`.
