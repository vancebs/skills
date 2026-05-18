---
name: claw-knowledge-base
description: >
  OpenClaw-only shared knowledge base skill. Defines a managed directory
  structure under KNOWLEDGE_BASE_DIR where all Markdown files are
  auto-indexed by OpenClaw. Agents can write knowledge into categorized
  subdirectories and retrieve it via memory_search semantic queries.
  NOT supported on other platforms.
  Trigger: use kb:// prefix to reference files in the knowledge base,
  e.g. kb://temp/result.md resolves to $KNOWLEDGE_BASE_DIR/temp/result.md.
platform: OpenClaw only
compatibility: >
  ⚠️ 本 skill 仅支持 OpenClaw 平台。非 OpenClaw 环境请勿使用。
  Python 3.9+ required for setup scripts (stdlib only).
keywords: [knowledge-base, openclaw, memory, shared, markdown, index, kb://]
triggers:
  - "kb://"
---

# Claw Knowledge Base Skill

> ⚠️ **仅支持 OpenClaw 平台。** 其他平台（本地 IDE、CLI、其他 agent 框架）不支持本 skill。

**功能：** 在 OpenClaw 中为多个 Agent 提供共享知识库。顶层目录下所有 `.md` 文件自动被 OpenClaw 索引，所有 Agent 均可通过 `memory_search` 进行语义检索，并按分类目录存入知识。

**两类操作：**

| 操作 | 说明 | 使用方式 |
|---|---|---|
| **读取（检索）** | 语义搜索已有知识 | `memory_search "<查询词>"` |
| **写入（存入）** | 将新知识写入对应目录的 `.md` 文件 | 按文件命名规范创建或更新文件 |

---

## 🔗 `kb://` 路径协议

### 定义

`kb://` 是本 skill 的触发词与路径协议。在任何上下文中出现 `kb://<path>` 时，Agent 应将其解析为知识库中的绝对路径。

**解析规则：**

```
kb://<path>  →  $KNOWLEDGE_BASE_DIR/<path>
```

| 示例 | 解析结果 |
|---|---|
| `kb://temp/review-result.md` | `$KNOWLEDGE_BASE_DIR/temp/review-result.md` |
| `kb://architecture/service-layer.md` | `$KNOWLEDGE_BASE_DIR/architecture/service-layer.md` |
| `kb://code-review-agent/context.md` | `$KNOWLEDGE_BASE_DIR/code-review-agent/context.md` |
| `kb://` （仅协议头，无路径）| `$KNOWLEDGE_BASE_DIR/`（根目录） |

**路径约束（正则）：** `^kb://([a-z0-9][a-z0-9-]*/)*([a-z0-9][a-z0-9-]*\.md)?$`
- `<path>` 中只允许小写字母、数字、连字符和 `/`
- 最多 2 层目录（`category/file.md`），不支持 3 层及以上
- 文件扩展名必须为 `.md`（若有文件名的话）

### 如何使用 `kb://` 路径

**读取文件：**
```bash
# 解析路径后直接读取
cat "$KNOWLEDGE_BASE_DIR/temp/review-result.md"
# 等价于
cat "$(python3 -c "import os; print(os.environ['KNOWLEDGE_BASE_DIR'] + '/temp/review-result.md')")"
```

**写入文件：**
```bash
# kb://temp/my-result.md → $KNOWLEDGE_BASE_DIR/temp/my-result.md
python3 -c "
import os
from pathlib import Path
kb = Path(os.environ['KNOWLEDGE_BASE_DIR'])
target = kb / 'temp' / 'my-result.md'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text('# My Result\n\n内容...', encoding='utf-8')
print(f'Written: {target}')
"
```

**检测 `kb://` 触发词（Python 辅助函数）：**
```python
import os, re
from pathlib import Path

KB_PROTO = re.compile(r'^kb://(.*)$')

def resolve_kb_path(uri: str) -> Path:
    """解析 kb://<path> 为绝对路径。"""
    m = KB_PROTO.match(uri)
    if not m:
        raise ValueError(f"不是合法的 kb:// URI: {uri!r}")
    kb_dir = os.environ.get("KNOWLEDGE_BASE_DIR", "")
    if not kb_dir:
        raise EnvironmentError("KNOWLEDGE_BASE_DIR 未设置")
    return Path(kb_dir) / m.group(1)

# 使用示例
path = resolve_kb_path("kb://temp/review-result.md")
# → Path("/home/user/project/knowledge-base/temp/review-result.md")
```

### 非正常路径处理

| 情况 | 处理动作 |
|---|---|
| `KNOWLEDGE_BASE_DIR` 未设置 | 停止并提示运行 Step 0 设置环境变量 |
| `<path>` 包含 `..` 或绝对路径段（路径穿越）| 拒绝解析，输出错误：`kb:// 路径不允许包含 '..' 或绝对路径` |
| 解析后的文件不存在（读取时）| 输出明确错误：`kb://<path> 文件不存在: <绝对路径>`；不自动创建 |
| `<path>` 超过 2 层目录深度 | 拒绝操作，输出错误：`kb:// 仅支持最多 2 层目录` |
| `<path>` 包含非法字符（大写/空格/中文等）| 拒绝操作，输出错误并给出正确格式示例 |

---

## ⚠️ Step 0 — 初始化环境变量（每次 OpenClaw 会话执行一次）

> OpenClaw 会在每次 agent 启动时恢复环境，但 `KNOWLEDGE_BASE_DIR` 需要明确设置。

```bash
# 检查 KNOWLEDGE_BASE_DIR 是否已由 openclaw.json 注入
echo $KNOWLEDGE_BASE_DIR

# 若未设置，手动设置（替换为实际路径）
export KNOWLEDGE_BASE_DIR="/path/to/your/knowledge-base"
```

**`KNOWLEDGE_BASE_DIR` 设置规则：**
- 必须为绝对路径，正则：`^/` (Linux/macOS) 或 `^[A-Za-z]:\\` (Windows)
- 推荐放在项目 workspace 下：`./knowledge-base`
- 设置后整个会话不得修改

---

> **路径约定**: 以下所有 `scripts/...` 路径均相对于本 Skill 目录（`.agents/skills/claw-knowledge-base/`）。

## ✅ Step 1 — 环境检查（首次使用时运行一次）

```bash
python3 scripts/check_env.py
```

脚本检查：
- `KNOWLEDGE_BASE_DIR` 已设置且为绝对路径
- 目录可读写（或可创建）
- `openclaw.json` 存在且 `memorySearch.extraPaths` 包含本目录
- 所有标准子目录已存在

输出示例：
```
✅ KNOWLEDGE_BASE_DIR: /home/user/project/knowledge-base
✅ 目录可读写
✅ openclaw.json: memorySearch.extraPaths 已包含本目录
✅ 子目录: architecture/ coding-standards/ troubleshooting/ ... (8个)
```

---

## ✅ Step 2 — 初始化目录结构（首次使用时运行一次）

```bash
python3 scripts/init_dirs.py
```

脚本在 `KNOWLEDGE_BASE_DIR` 下创建所有标准子目录，并在每个目录写入 `README.md` 说明文件。已存在的文件不会覆盖。

---

## ✅ Step 3 — 配置 openclaw.json（首次使用时，人工操作一次）

在项目的 `openclaw.json` 中，将 `KNOWLEDGE_BASE_DIR` 路径加入所有 Agent 的 `memorySearch.extraPaths`：

```json
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "extraPaths": [
          "${KNOWLEDGE_BASE_DIR}"
        ]
      }
    }
  },
  "env": {
    "KNOWLEDGE_BASE_DIR": "/path/to/your/knowledge-base"
  }
}
```

> **注意：** 修改 `openclaw.json` 后需要重启 OpenClaw 或重新加载项目配置，新的 `extraPaths` 才能生效。

### Checklist: Step 3 验证

- [ ] `openclaw.json` 已编辑，`extraPaths` 包含 `${KNOWLEDGE_BASE_DIR}` 或实际路径
- [ ] `env.KNOWLEDGE_BASE_DIR` 已设置为实际绝对路径
- [ ] OpenClaw 已重启 / 项目配置已重新加载
- [ ] 运行 `memory_search "test"` 无报错，返回结果包含 knowledge-base 目录下的内容

---

## 📁 目录结构参考

```
knowledge-base/
├── architecture/         # 系统架构文档（层级、模块划分、关键设计决策）
├── coding-standards/     # 编码规范和最佳实践
├── troubleshooting/      # 常见问题和解决方案
├── release-notes/        # 版本发布记录
├── code-review/          # 存档 code review 报告
├── temp/                 # agent 之间临时文件分享（定期清理）
├── onboarding/           # 新成员入职指南
└── {agent_def_dir}/      # 各 agent 自定义目录（见下方说明）
```

### 各目录使用说明

| 目录 | 写入时机 | 典型文件名示例 |
|---|---|---|
| `architecture/` | 系统层级变更、新模块引入、重大架构决策 | `service-layer-overview.md` |
| `coding-standards/` | 编码规范更新、新语言/框架规范建立 | `java-naming-rules.md` |
| `troubleshooting/` | 反复出现的问题、排查步骤确认后 | `gerrit-ssh-connection-fail.md` |
| `release-notes/` | 每个里程碑 / 版本发布后 | `v2.3.0-release-notes.md` |
| `code-review/` | 存档 code review 报告（每次审查生成一份）| `2026-05-18_12345.md` |
| `temp/` | agent 之间一次性文件传递 | `agent-a-to-b-handoff.md` |
| `onboarding/` | 环境搭建、常用命令、项目结构说明 | `dev-environment-setup.md` |
| `{agent_def_dir}/` | 各 agent 私有的持久化知识 | `<agent-name>-context.md` |

### `{agent_def_dir}` 命名规则

- 格式正则：`^[a-z][a-z0-9-]*$`（小写字母 + 数字 + 连字符，以字母开头）
- 示例：`code-review-agent/`, `release-manager/`, `qa-bot/`
- 每个 agent 只写入自己的目录，**不得修改其他 agent 的私有目录**

---

## 📝 知识写入规范

### 文件格式要求

- **格式**：Markdown（`.md`）
- **编码**：UTF-8
- **文件名**：小写英文 + 连字符，正则：`^[a-z0-9][a-z0-9-]*\.md$`
  - ✅ `kernel-driver-guide.md`
  - ❌ `Kernel Driver Guide.md`、`kernel_driver.md`、`guide.txt`

### Markdown 内容要求

```markdown
# 文档标题（必须有，且明确反映内容主题）

## 背景（可选）
<简短说明此文档的背景或适用场景>

## 内容主体
<正文，使用二级/三级标题组织>

## 关键词（可选，提升检索命中率）
<!-- keywords: keyword1, keyword2, keyword3 -->
```

**必须满足：**
- [ ] 文件第一行为 `# 标题`（H1），正则：`^# \S+.*`
- [ ] 标题明确描述内容，不使用 "temp"、"test"、"misc"、"notes" 等模糊标题
- [ ] 代码片段使用 fenced code block（` ```language ... ``` `）
- [ ] 文件大小 ≤ 1 MB（单文件；超大内容请拆分）

---

## 🔍 知识检索使用方式

### 基本检索

在 OpenClaw 中，直接使用 `memory_search` 工具：

```
memory_search "gerrit SSH connection refused"
memory_search "Java 命名规范 接口"
memory_search "v2.3 release"
```

### 检索最佳实践

| 场景 | 推荐查询写法 |
|---|---|
| 排查问题 | 用具体症状描述，如 `"SSH port 29418 connection timeout"` |
| 查找规范 | 用规范名称 + 关键字，如 `"Java 变量命名 camelCase"` |
| 查找历史决策 | 用决策描述，如 `"service 层拆分 决策 2025"` |
| 查找 agent 私有信息 | 加 agent 目录名前缀，如 `"code-review-agent context"` |

### 写入后的检索生效时间

OpenClaw 对新文件的索引更新有延迟（通常 < 60 秒）。若写入后立即检索未命中，等待 60 秒后重试。

---

## 📋 知识写入流程

```mermaid
flowchart TD
    A([需要写入知识]) --> B{确定分类}
    B -- 架构/设计 --> C[architecture/]
    B -- 规范 --> D[coding-standards/]
    B -- 问题解决 --> E[troubleshooting/]
    B -- 版本记录 --> F[release-notes/]
    B -- CR报告存档 --> G[code-review/]
    B -- 临时传递 --> H[temp/]
    B -- 入职信息 --> I[onboarding/]
    B -- agent私有 --> J[{agent_def_dir}/]
    C & D & E & F & G & H & I & J --> K[确认文件名符合规范]
    K --> L{文件是否已存在?}
    L -- 否 --> M[创建新文件，包含 H1 标题]
    L -- 是 --> N[追加内容，更新日期]
    M & N --> O[验证 Markdown 格式]
    O --> P([写入完成])
```

### Checklist: 写入知识前确认

- [ ] 已确认写入的目录正确（参考目录说明表）
- [ ] 文件名符合规范：`^[a-z0-9][a-z0-9-]*\.md$`
- [ ] 文件包含明确的 H1 标题（`# 标题`）
- [ ] 若文件已存在，使用追加方式，不删除原有内容
- [ ] 不包含敏感信息（密码、token、内网 IP）

---

## ⛔ 约束与禁止事项

### 不支持的场景

| 场景 | 原因 | 处理动作 |
|---|---|---|
| 非 OpenClaw 平台使用本 skill | `memory_search` 不可用 | 停止并告知用户：本 skill 仅支持 OpenClaw |
| `KNOWLEDGE_BASE_DIR` 未设置 | 无法定位知识库 | 停止，输出 Step 0 操作指引 |
| `KNOWLEDGE_BASE_DIR` 目录不可写 | 权限不足 | 停止，输出 `ls -la` 检查命令和权限修复建议 |
| `openclaw.json` 未配置 `extraPaths` | 新文件不会被索引 | 不阻止写入，但输出 WARNING 提示用户完成 Step 3 |
| 写入非 `.md` 格式文件 | OpenClaw 索引不支持 | 拒绝写入，输出"仅支持 .md 文件" |
| 单文件超过 1 MB | 影响索引性能 | 写入前检查大小；超限时建议拆分，不阻止但输出 WARNING |
| `temp/` 目录下文件永久保留 | temp 目录用于临时传递 | 每次写入 temp/ 后，在文件头标注 `expires: YYYY-MM-DD`，agent 读取后负责删除 |

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

### KNOWLEDGE_BASE_DIR 来源优先级

| 优先级 | 来源 | 示例 |
|---|---|---|
| 1 ✅ 推荐 | `openclaw.json` 的 `env` 字段（OpenClaw 自动注入）| `"KNOWLEDGE_BASE_DIR": "/abs/path"` |
| 2 | 手动 `export`（会话内临时） | `export KNOWLEDGE_BASE_DIR=...` |
| 3 | `.env` 文件（需 OpenClaw 支持加载）| `KNOWLEDGE_BASE_DIR=/abs/path` |

---

## 文件清单

```
claw-knowledge-base/
├── SKILL.md
├── README.md
└── scripts/
    ├── check_env.py    ← 环境检查（验证 KNOWLEDGE_BASE_DIR、openclaw.json、子目录）
    └── init_dirs.py    ← 初始化标准子目录（幂等，不覆盖已有文件）
```
