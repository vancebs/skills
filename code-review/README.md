# code-review

按需 Code Review skill。当 agent 收到 Gerrit 变更信息时，自动获取 patch 并执行代码审查。

## 触发条件

收到以下任意内容时使用：
- Gerrit 变更页面链接（`http://...` 或 `https://...`）
- Change number（纯数字，如 `12345`）
- Change-Id（`I` + 40位十六进制）
- Commit SHA（7~40 位十六进制）
- Gerrit stream event JSON 文本

## 快速开始

```bash
# 1. 环境检查
python3 scripts/check_env.py

# 2. 设置 Gerrit 环境变量
export GERRIT_URL="https://gerrit.example.com"
export GERRIT_USERNAME="john.doe"
export GERRIT_HTTP_PASSWORD="your-http-token"

# 3. 执行审查（触发词：Gerrit URL / change number / Change-Id）
# Agent 收到变更信息后自动触发 SKILL.md 中的工作流
```

详细说明见 [SKILL.md](SKILL.md)。
