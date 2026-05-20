# code-review

按需 Code Review skill。当 agent 收到 Gerrit 变更信息时，自动获取 patch 并执行代码审查，生成结构化报告。**不对 Gerrit 做任何写操作。**

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

# 2. 确保 gerrit-api skill 已配置（见 gerrit-api/README.md）
```

### 可选配置

| 配置项（JSON key / 环境变量） | 默认值 | 说明 |
|---|---|---|
| `CODE_REVIEW_SKIP_PATTERNS` | — | 跳过文件 glob，逗号分隔，如 `*.md,*.json` |

配置文件路径（优先级由高到低）：
1. `$WORKSPACE/.config/code-review.json`
2. `~/.config/code-review.json`

或直接设置环境变量：
```bash
export CODE_REVIEW_SKIP_PATTERNS="*.min.js,*.generated.*"
```

## 依赖

| Skill | 说明 |
|---|---|
| `gerrit-api` | 必须安装，提供所有 Gerrit 只读操作 |
| `T2MCodingRule` | 必须安装，提供审查规范 |

详细说明见 [SKILL.md](SKILL.md)。

详细说明见 [SKILL.md](SKILL.md)。
