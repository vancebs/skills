---
name: claw-knowledge-base
description: >
  This skill should be used when the user references "kb://", asks to
  "save to knowledge base", "read from knowledge base", "store review result",
  "search knowledge base", or manages shared Markdown files under
  KNOWLEDGE_BASE_DIR on OpenClaw. Use kb://<path> to reference files,
  e.g. kb://temp/result.md. OpenClaw platform only — not supported elsewhere.
platform: OpenClaw only
compatibility: >
  ⚠️ OpenClaw platform only. Python 3.9+ required for setup scripts (stdlib only).
keywords:
  - knowledge-base
  - openclaw
  - memory
  - shared
  - markdown
  - index
  - kb://
triggers:
  - "kb://"
  - knowledge base
  - 知识库
  - save to kb
  - read from kb
  - KNOWLEDGE_BASE_DIR
---

# Claw Knowledge Base Skill

> ⚠️ **仅支持 OpenClaw 平台。** 其他平台（本地 IDE、CLI、其他 agent 框架）不支持本 skill。

**功能：** 在 OpenClaw 中为多个 Agent 提供共享知识库。顶层目录下的 `.md` 文件会被索引，Agent 可通过 `memory_search` 检索，并按分类目录写入知识。

**两类核心操作：**
- **读取**：用 `memory_search` 做语义检索，或按 `kb://` 路径直接读取文件
- **写入**：把 Markdown 内容写入 `KNOWLEDGE_BASE_DIR` 下的合适分类目录

## ⚡ 操作速查

| 操作 | 方法 | 示例 |
|---|---|---|
| 语义检索 | `memory_search "关键词"` | `memory_search "gerrit SSH"` |
| 路径读取 | `cat $KNOWLEDGE_BASE_DIR/<path>` | `cat $KNOWLEDGE_BASE_DIR/temp/x.md` |
| 路径引用 | `kb://<path>` | `kb://code-review/2024-01-15_12345.md` |
| 写入文件 | Python `Path.write_text()` | 见工作流示例 |
| 初始化目录 | `python3 scripts/init_dirs.py` | — |
| 环境检查 | `python3 scripts/check_env.py` | — |

## 🚀 Quick Start

1. **设置知识库目录**（选择一种方式）

   **方式 A — 配置文件（推荐）**：创建 `$WORKSPACE/.config/claw-knowledge-base.json`（或 `~/.config/claw-knowledge-base.json`）：
   ```json
   { "KNOWLEDGE_BASE_DIR": "/path/to/your/knowledge-base" }
   ```

   **方式 B — 环境变量**：
   ```bash
   export KNOWLEDGE_BASE_DIR="/path/to/your/knowledge-base"
   ```

   也可在 `openclaw.json` 的 `env` 字段中设置：
   ```json
   { "env": { "KNOWLEDGE_BASE_DIR": "/path/to/your/knowledge-base" } }
   ```

2. **检查环境并初始化目录**
   ```bash
   python3 scripts/check_env.py
   python3 scripts/init_dirs.py
   ```
3. **在 `openclaw.json` 中加入索引路径**
   ```json
   {
     "agents": {
       "defaults": {
         "memorySearch": {
           "extraPaths": ["${KNOWLEDGE_BASE_DIR}"]
         }
       }
     },
     "env": {
       "KNOWLEDGE_BASE_DIR": "/path/to/your/knowledge-base"
     }
   }
   ```
4. **读取与写入**
   ```bash
   memory_search "gerrit SSH connection refused"
   cat "$KNOWLEDGE_BASE_DIR/temp/review-result.md"
   ```
   ```bash
   python3 - <<'PY'
   import os
   from pathlib import Path
   target = Path(os.environ['KNOWLEDGE_BASE_DIR']) / 'temp' / 'my-result.md'
   target.parent.mkdir(parents=True, exist_ok=True)
   target.write_text('# My Result\n\n内容...', encoding='utf-8')
   print(target)
   PY
   ```

> **路径约定**: 以下所有 `scripts/...` 路径均相对于本 Skill 目录（`.agents/skills/claw-knowledge-base/`）。

## 🔗 `kb://` 路径参考

`kb://<path>` 会解析为 `$KNOWLEDGE_BASE_DIR/<path>`。

| 示例 | 解析结果 |
|---|---|
| `kb://temp/review-result.md` | `$KNOWLEDGE_BASE_DIR/temp/review-result.md` |
| `kb://architecture/service-layer.md` | `$KNOWLEDGE_BASE_DIR/architecture/service-layer.md` |
| `kb://code-review-agent/context.md` | `$KNOWLEDGE_BASE_DIR/code-review-agent/context.md` |
| `kb://` | `$KNOWLEDGE_BASE_DIR/` |

> 📖 完整目录结构说明和最佳实践见 [`references/directory-guide.md`](references/directory-guide.md)  
> 📖 `kb://` 路径用法、`memory_search` 检索技巧、多 Agent 协作模式见 [`references/search-patterns.md`](references/search-patterns.md)

## 📚 参考文件

| 文件 | 内容 |
|---|---|
| [`references/directory-guide.md`](references/directory-guide.md) | 目录结构详解、命名规范、检索示例、最佳实践 |
| [`references/search-patterns.md`](references/search-patterns.md) | `kb://` 路径用法、`memory_search` 检索技巧、多 Agent 协作模式 |

---

## 🔄 常见 Agent 工作流

### 工作流 1 — Code Review Agent 存档报告

```
输入：code review 完成后的报告文本

Step 1: 确认 KNOWLEDGE_BASE_DIR 已设置
Step 2: 写入存档目录
  目标路径: kb://code-review/YYYY-MM-DD_<change_number>.md
  内容格式: Markdown，包含变更详情、审查结果、问题列表

Step 3: （可选）同时写临时文件供其他 Agent 消费
  目标路径: kb://temp/review-<change_number>.md
  文件头需包含: expires: YYYY-MM-DD
```

**示例（Python）：**
```python
from pathlib import Path
from datetime import date
import os

kb = Path(os.environ['KNOWLEDGE_BASE_DIR'])
change = "12345"
report_path = kb / 'code-review' / f'{date.today().isoformat()}_{change}.md'
report_path.write_text(report_content, encoding='utf-8')
```

---

### 工作流 2 — 检索历史问题解决方案

```
场景：遇到 Gerrit SSH 连接超时问题，先检索知识库

Step 1: memory_search "gerrit SSH timeout connection refused"
Step 2: 如有结果，读取对应文件
  cat "$KNOWLEDGE_BASE_DIR/troubleshooting/gerrit-ssh.md"
  或通过 kb://troubleshooting/gerrit-ssh.md 引用
Step 3: 按照文件中的解决方案操作
Step 4: 如发现新解法，追加到同一文件（先读后写）
```

---

### 工作流 3 — 多 Agent 传递临时数据

```
Agent A 写入:
  kb://temp/analysis-<task_id>.md   ← 包含 expires 字段

Agent B 读取和清理:
  1. memory_search "temp analysis <task_id>"
  2. 读取文件内容处理业务逻辑
  3. 删除临时文件（temp/ 目录不保留持久文件）
```

---

### 工作流 4 — 初始化新知识库

```bash
# Step 1: 设置路径（config 文件或环境变量）
# Step 2: 检查环境
python3 scripts/check_env.py

# Step 3: 创建标准目录结构
python3 scripts/init_dirs.py

# Step 4: 在 openclaw.json 中注册索引路径（见 Quick Start Step 3）
```

---



### 不支持的场景

| 场景                               | 原因                  | 处理动作                                                    |
| -------------------------------- | ------------------- | ------------------------------------------------------- |
| 非 OpenClaw 平台使用本 skill           | `memory_search` 不可用 | 停止并告知用户：本 skill 仅支持 OpenClaw                            |
| `KNOWLEDGE_BASE_DIR` 未设置         | 无法定位知识库             | 停止，输出 Quick Start 操作指引                                  |
| `KNOWLEDGE_BASE_DIR` 目录不可写       | 权限不足                | 停止，输出 `ls -la` 检查命令和权限修复建议                              |
| `openclaw.json` 未配置 `extraPaths` | 新文件不会被索引            | 不阻止写入，但输出 WARNING 提示用户完成 Quick Start 第 3 步              |
| 写入非 `.md` 格式文件                   | OpenClaw 索引不支持      | 拒绝写入，输出"仅支持 .md 文件"                                     |
| 单文件超过 1 MB                       | 影响索引性能              | 写入前检查大小；超限时建议拆分，不阻止但输出 WARNING                          |
| `temp/` 目录下文件永久保留                | temp 目录用于临时传递       | 每次写入 temp/ 后，在文件头标注 `expires: YYYY-MM-DD`，agent 读取后负责删除 |

### 明确禁止的操作

- ⛔ **禁止写入密码、API token、内网 IP、私钥等敏感信息**：知识库对所有 Agent 可见
- ⛔ **禁止修改其他 Agent 的私有目录（`{agent_def_dir}/`）**：每个 Agent 只写自己的目录
- ⛔ **禁止删除 `architecture/`、`coding-standards/` 等标准目录**
- ⛔ **禁止在 `KNOWLEDGE_BASE_DIR` 根目录直接写入文件**（必须进入子目录）
- ⛔ **禁止使用非 Markdown 格式（`.txt`、`.json`、`.yaml` 等）写入知识**：这些文件不会被索引
- ⛔ **禁止在文件名中使用空格、大写字母、下划线或中文**

### 边界条件

| 参数 | 范围 | 超限行为 |
|---|---|---|
| 单个 `.md` 文件大小 | ≤ 1 MB | 超限 → WARNING，建议拆分；不阻止写入 |
| 文件名长度 | ≤ 128 字符（含 `.md`） | 超限 → 拒绝写入，exit 1 |
| 目录深度 | 最多 2 层（`{category}/{file.md}`） | 不支持 3 层及更深的子目录结构 |
| `memory_search` 查询字符串长度 | ≤ 512 字符 | 超限 → 截断为前 512 字符，输出 WARNING |

### 幂等性声明

| 操作 | 幂等性 | 说明 |
|---|---|---|
| `init_dirs.py` 创建目录 | ✅ 幂等 | 已存在的目录和文件不覆盖 |
| `check_env.py` 检查 | ✅ 幂等 | 只读检查，可多次运行 |
| 向已有文件追加内容 | ⚠️ 非幂等（无保护）| 重复运行会重复追加；调用方负责检查内容是否已存在 |
| 创建新文件 | ❌ 非幂等 | 已存在时必须先读取再决定追加或跳过，不得覆盖 |

---

## 🔧 Troubleshooting

| 症状 | 诊断 | 解决方案 |
|---|---|---|
| `KNOWLEDGE_BASE_DIR` 未设置 | `echo $KNOWLEDGE_BASE_DIR` 为空 | 创建配置文件或 `export KNOWLEDGE_BASE_DIR=...` |
| `memory_search` 无结果 | 文件未被索引 | 检查 `openclaw.json` 中 `extraPaths` 是否包含 `KNOWLEDGE_BASE_DIR` |
| `memory_search` 返回过期内容 | OpenClaw 索引未刷新 | 重启 OpenClaw agent 或等待自动重新索引 |
| 写入权限拒绝 | 目录不可写 | `ls -la $KNOWLEDGE_BASE_DIR`，`chmod u+w` 修复 |
| `init_dirs.py` 报错 | Python 版本 < 3.9 | `python3 --version` 确认；升级 Python 3.9+ |
| `kb://` 路径解析失败 | `KNOWLEDGE_BASE_DIR` 含尾部斜杠 | 确保路径格式为 `/path/to/kb`（不含尾部 `/`） |
| 新写入文件不出现在搜索结果 | 索引延迟 | 等待 10-30 秒；若长时间未出现，检查 `extraPaths` 配置 |
| 文件写入后内容被覆盖 | 并发写同一文件 | 多 Agent 协作时使用唯一文件名（如加 agent 名或时间戳） |

### 快速诊断命令

```bash
# 检查环境
python3 scripts/check_env.py

# 确认目录可读写
ls -la "$KNOWLEDGE_BASE_DIR"

# 查看已有文件
find "$KNOWLEDGE_BASE_DIR" -name "*.md" | head -20

# 验证 openclaw.json 配置
cat openclaw.json | python3 -m json.tool | grep -A3 '"extraPaths"'
```

---

## 📋 文件命名规范

| 目录 | 命名格式 | 示例 |
|---|---|---|
| `code-review/` | `YYYY-MM-DD_<change_number>.md` | `2024-01-15_12345.md` |
| `troubleshooting/` | `<problem-keyword>.md` | `gerrit-ssh-timeout.md` |
| `architecture/` | `<component>-<aspect>.md` | `auth-service-overview.md` |
| `temp/` | `<task>-<agent>-<id>.md` | `review-code-review-agent-12345.md` |
| 通用规则 | 小写字母 + 连字符，≤ 128 字符 | — |

---

## 📦 依赖说明

| 依赖 | 类型 | 说明 |
|---|---|---|
| OpenClaw 平台 | 运行时（必须） | `memory_search` API 由 OpenClaw 提供，非 OpenClaw 环境无法使用 |
| Python 3.9+ | 运行时（可选） | 仅 `check_env.py` 和 `init_dirs.py` 需要，核心读写操作不依赖 Python |
| `KNOWLEDGE_BASE_DIR` | 环境变量 | 指向知识库根目录，必须在 `openclaw.json` 或配置文件中设置 |

---
