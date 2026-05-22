# niuma-cli

面向开发者日常工作记录的本地命令行工具。V1 当前支持项目、Todo、Progress、标签配置和状态查询，数据默认保存到 `~/.niuma/niuma.db`。

## 安装开发环境

```bash
uv sync
```

## 常用命令

```bash
uv run niuma project create 电商系统
uv run niuma project rename 1 支付系统
uv run niuma project list

uv run niuma todo add "修复登录页验证码报错" --content "复现路径、影响范围和下一步处理计划" -p 1 -t Bug
uv run niuma todo modify 1 --title "修复登录页验证码重试报错" --content "已确认错误恢复路径" -p 1 -t Bug
uv run niuma todo done 1
uv run niuma todo list
uv run niuma todo focus 1
uv run niuma todo stop
uv run niuma todo focus-log 1 --from "09:30" --to "11:30"
uv run niuma todo focus-log 1 --duration "2h"

uv run niuma progress log "完成支付接口联调" --content "覆盖下单、回调和异常重试链路" -p 1 -t Feature
uv run niuma progress modify 1 --title "完成支付接口回归" --content "已补齐回调失败场景" -p 1 -t Feature
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
