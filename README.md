# niuma-cli

面向开发者日常工作记录的本地命令行工具。V1 当前支持项目、Todo、Progress、标签配置和状态查询，数据默认保存到 `~/.niuma/niuma.db`。

## 安装开发环境

```bash
uv sync
```

## 常用命令

```bash
uv run niuma project create 电商系统
uv run niuma project list

uv run niuma todo add "修复登录页验证码报错" -p 1 -t Bug
uv run niuma todo done 1
uv run niuma todo list
uv run niuma todo focus 1
uv run niuma todo stop
uv run niuma todo focus-log 1 --from "09:30" --to "11:30"
uv run niuma todo focus-log 1 --duration "2h"

uv run niuma progress log "和前端联调支付接口" -p 1 -t Feature
uv run niuma progress list

uv run niuma daily generate
uv run niuma daily generate --week
NIUMA_LLM_BASE_URL="http://192.0.2.10:8080" NIUMA_LLM_API_KEY="sk-..." uv run niuma daily generate

uv run niuma chill start "等待上游环境配置"
uv run niuma chill end
uv run niuma stats week
uv run niuma stats month

uv run niuma config get db.path
uv run niuma config set db.path "/tmp/niuma.db"
uv run niuma config set llm.base_url "http://192.0.2.10:8080"
uv run niuma config set llm.model "gpt-5.5"
uv run niuma config tags list
uv run niuma status
```

## 验证

```bash
uv run pytest
```
