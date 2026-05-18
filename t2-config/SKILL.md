---
name: t2-config
description: Centralized configuration management for agent skills. Use cfg://<namespace>/<key> to read or write configuration values. Triggers on cfg:// prefix.
license: Apache-2.0
compatibility: Requires python3 (≥3.9). No pip dependencies.
keywords: [config, configuration, cfg, settings]
triggers: ["cfg://"]
---

# t2-config Skill

**功能：** 集中管理 agent skills 的配置。所有配置以 `cfg://<namespace>/<key>` 协议寻址，存储于 `${CFG_DIR}/<namespace>.json`（flat JSON 文件）。

**脚本（Python stdlib，无需 pip）：**

| 脚本 | 用途 |
|---|---|
| `scripts/t2_config.py` | 读写配置值（get/set/list/delete） |
| `scripts/check_env.py` | 检查 Python 版本与 CFG_DIR 设置 |

> **路径约定**: 以下所有 `scripts/...` 路径均相对于本 Skill 目录（`.agents/skills/t2-config/`）。

---

## ✅ Setup Checklist

### Step 0 — Set CFG_DIR

```bash
# Linux / macOS
export CFG_DIR="$(pwd)/config"

# Windows CMD
set CFG_DIR=%CD%\config

# Windows PowerShell
$env:CFG_DIR = "$(Get-Location)\config"
```

`CFG_DIR` 必须为绝对路径，且**不得**位于版本控制目录下（避免意外提交凭据）。

### Step 1 — Check Environment

```bash
python3 scripts/check_env.py
```

脚本检查：Python 版本 ≥ 3.9、`CFG_DIR` 已设置、目录可写（不存在则自动创建）。

### Step 2（可选）— Initialize Namespace

```bash
python3 scripts/t2_config.py set gerrit-api/url "https://gerrit.example.com"
```

---

## 📋 Operations

| Operation | Command |
|---|---|
| Read value | `python3 scripts/t2_config.py get <namespace>/<key>` |
| Write value | `python3 scripts/t2_config.py set <namespace>/<key> <value>` |
| List namespace | `python3 scripts/t2_config.py list <namespace>` |
| Delete key | `python3 scripts/t2_config.py delete <namespace>/<key>` |
| List all namespaces | `python3 scripts/t2_config.py list` |

---

## 🔗 `cfg://` 路径协议

### 定义

`cfg://` 是本 skill 的触发词与路径协议。在任何上下文中出现 `cfg://<namespace>/<key>` 时，Agent 应将其解析为：

```
cfg://<namespace>/<key>  →  ${CFG_DIR}/<namespace>.json  →  key "<key>"
```

**路径约束（正则）：** `^cfg://([a-z][a-z0-9-]*)/([a-z][a-z0-9_-]*)$`
- `<namespace>`：小写字母开头，仅含小写字母、数字、连字符
- `<key>`：小写字母开头，仅含小写字母、数字、下划线、连字符
- 不支持嵌套 key（key 不含 `/`）

### 使用示例

```bash
# 写入
python3 scripts/t2_config.py set gerrit-api/url "https://gerrit.example.com"
python3 scripts/t2_config.py set gerrit-api/ssh_port 29418
python3 scripts/t2_config.py set agent-code-review/test_mode true

# 读取
python3 scripts/t2_config.py get gerrit-api/url

# 列出命名空间所有 key
python3 scripts/t2_config.py list gerrit-api

# 列出所有命名空间
python3 scripts/t2_config.py list

# 删除 key
python3 scripts/t2_config.py delete gerrit-api/ssh_key
```

---

## 📦 Namespace Registry

标准命名空间（供其他 skills 使用）：

| Namespace | Skill | Key 示例 |
|---|---|---|
| `gerrit-api` | gerrit-api | `url`, `username`, `password`, `ssh_host`, `ssh_port`, `ssh_username`, `ssh_key` |
| `atlassian` | atlassian-jira-confluence | `url`, `username`, `api_token` |
| `agent-code-review` | agent-code-review | `test_mode`, `test_channel` |
| `code-review` | code-review | `test_mode`, `skip_file_patterns` |

---

## Value 类型自动检测（set 命令）

`set` 命令会自动将字符串参数转换为合适的 JSON 类型：

| 输入字符串 | 存储类型 |
|---|---|
| `"true"` / `"false"` | `bool` |
| `"null"` | `null` |
| 整数字符串，如 `"29418"` | `int` |
| 浮点字符串，如 `"3.14"` | `float` |
| 其他 | `string` |
| JSON array/object（以 `[` 或 `{` 开头）| `array` / `object` |

---

## 非正常路径处理

| 情况 | 处理动作 |
|---|---|
| `CFG_DIR` 未设置 | 拒绝所有操作，输出：`❌ CFG_DIR 未设置 → 解决方法: export CFG_DIR="$(pwd)/config"` |
| namespace 文件不存在（get/list） | 视为空命名空间，输出空结果 |
| key 不存在（get） | 输出错误信息，exit 1 |
| key 格式不合法 | 输出格式说明，exit 1 |
| JSON 解析错误 | 输出错误信息，exit 1 |
| 写权限被拒绝 | 输出错误信息，exit 1 |
| key 包含 `/`（嵌套不支持）| 输出错误信息，exit 1 |

---

## ⛔ 约束与禁止事项

- 仅支持 JSON-serializable values（string, number, boolean, array, object）
- 不得将 `CFG_DIR` 设置为版本控制目录下的路径（避免意外提交凭据）
- `cfg://` 路径正则：`^cfg://([a-z][a-z0-9-]*)/([a-z][a-z0-9_-]*)$`
- 不支持嵌套 key（key 必须是 flat string，不含 `/`）
- CFG_DIR 未设置时拒绝所有操作并提示用户配置

Add to `.gitignore`:
```
config/
```

---

## 文件清单

```
t2-config/
├── SKILL.md
├── README.md
└── scripts/
    ├── t2_config.py   ← 配置读写 CLI（get/set/list/delete）
    └── check_env.py   ← 环境检查（Python 版本、CFG_DIR）
```
