# Knowledge Base Directory Guide

> **来源：** claw-knowledge-base skill 参考文件。管理知识库目录结构、命名规范、检索方式时参考本文档。

## 目录结构详解

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

## 文件命名规范

- 文件格式：Markdown（`.md`）
- 编码：UTF-8
- 文件名正则：`^[a-z0-9][a-z0-9-]*\.md$`
- 推荐使用主题明确、可检索的名字

**示例：**
- ✅ `kernel-driver-guide.md`
- ✅ `gerrit-ssh-connection-fail.md`
- ❌ `Kernel Driver Guide.md`
- ❌ `kernel_driver.md`
- ❌ `guide.txt`

## 各类目录的内容要求

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
- [ ] 标题明确描述内容，不使用 `temp`、`test`、`misc`、`notes` 等模糊标题
- [ ] 代码片段使用 fenced code block（` ```language ... ``` `）
- [ ] 文件大小 ≤ 1 MB（超大内容请拆分）
- [ ] 不包含敏感信息（密码、token、内网 IP、私钥）

## 如何高效使用 memory_search

### 基本检索示例

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

## `kb://` 路径解析规则

`kb://<path>` 会解析为 `$KNOWLEDGE_BASE_DIR/<path>`。

| 示例 | 解析结果 |
|---|---|
| `kb://temp/review-result.md` | `$KNOWLEDGE_BASE_DIR/temp/review-result.md` |
| `kb://architecture/service-layer.md` | `$KNOWLEDGE_BASE_DIR/architecture/service-layer.md` |
| `kb://code-review-agent/context.md` | `$KNOWLEDGE_BASE_DIR/code-review-agent/context.md` |
| `kb://` | `$KNOWLEDGE_BASE_DIR/` |

**路径约束：**
- 正则：`^kb://([a-z0-9][a-z0-9-]*/)*([a-z0-9][a-z0-9-]*\.md)?$`
- 只允许小写字母、数字、连字符和 `/`
- 最多 2 层目录（`category/file.md`）
- 文件扩展名必须为 `.md`

### 路径解析示例（Python）

```python
import os, re
from pathlib import Path

KB_PROTO = re.compile(r'^kb://(.*)$')

def resolve_kb_path(uri: str) -> Path:
    m = KB_PROTO.match(uri)
    if not m:
        raise ValueError(f"不是合法的 kb:// URI: {uri!r}")
    kb_dir = os.environ.get("KNOWLEDGE_BASE_DIR", "")
    if not kb_dir:
        raise EnvironmentError("KNOWLEDGE_BASE_DIR 未设置")
    return Path(kb_dir) / m.group(1)
```

### 非正常路径处理

| 情况 | 处理动作 |
|---|---|
| `KNOWLEDGE_BASE_DIR` 未设置 | 停止并提示运行 Quick Start 设置环境变量 |
| `<path>` 包含 `..` 或绝对路径段 | 拒绝解析并报错 |
| 解析后的文件不存在（读取时） | 输出明确错误，不自动创建 |
| `<path>` 超过 2 层目录深度 | 拒绝操作 |
| `<path>` 包含非法字符 | 拒绝操作并给出正确格式示例 |

## 知识组织最佳实践

- 先确定分类，再创建文件，避免把长期知识写进 `temp/`
- 优先追加已有主题文件，减少重复文档
- 标题、文件名、关键词尽量包含业务词和问题症状，提升召回率
- `code-review/` 适合归档审查结果，`troubleshooting/` 适合沉淀已验证的问题解法
- `temp/` 文件应写入过期时间并在交接完成后清理
- agent 私有知识放入自己的 `{agent_def_dir}/`，不要跨目录修改他人内容
