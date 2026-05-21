# Knowledge Base Search & Usage Patterns

> **来源：** claw-knowledge-base skill 参考文件。覆盖 kb:// 路径用法、memory_search 检索技巧、多 Agent 协作模式。

---

## 一、`kb://` 路径用法

### 路径规则

`kb://<path>` 解析为 `$KNOWLEDGE_BASE_DIR/<path>`，遵循以下规则：

| 规则 | 说明 | 示例 |
|---|---|---|
| 相对路径 | 相对于 `KNOWLEDGE_BASE_DIR` 根目录 | `kb://temp/x.md` |
| 仅支持 `.md` | 非 `.md` 文件不被索引 | `kb://temp/x.md` ✅, `kb://temp/x.json` ❌ |
| 最多 2 层 | 不支持 3 层及更深子目录 | `kb://a/b.md` ✅, `kb://a/b/c.md` ❌ |
| 文件名小写 + 连字符 | 禁止空格、大写、下划线 | `kb://temp/my-result.md` ✅ |

### 常用路径示例

```
kb://temp/review-result.md          → 临时 code review 报告（读后需删）
kb://code-review/2024-01-15_12345.md → 存档的 code review 报告
kb://architecture/service-layer.md  → 系统架构文档
kb://coding-standards/java-guide.md → Java 编码规范补充
kb://troubleshooting/gerrit-ssh.md  → Gerrit SSH 常见问题
```

---

## 二、`memory_search` 检索技巧

### 基本用法

```bash
memory_search "gerrit SSH connection refused"
memory_search "Java 命名规范 变量"
memory_search "code review FAIL 原因"
```

### 提高检索精度的技巧

| 技巧 | 说明 | 示例 |
|---|---|---|
| 用关键词而非问句 | 关键词匹配优于自然语言 | `"gerrit SSH key"` 优于 `"如何配置 gerrit SSH"` |
| 中英文混用 | 文档可能含中英文混写 | `"commit message Root Cause"` |
| 限定目录关键词 | 结合目录名可缩小范围 | `"architecture 服务层"` |
| 多词组合 | 用空格分隔多个关键词 | `"code review FAIL 安全 漏洞"` |

### 按目录检索最佳实践

```bash
# 检索架构文档
memory_search "architecture 模块 层级"

# 检索编码规范
memory_search "coding-standards Java C++ 命名"

# 检索问题解决方案
memory_search "troubleshooting 错误 connection refused"

# 检索历史 code review 报告
memory_search "code-review 2024 FAIL ERROR"
```

---

## 三、写入知识库的标准模式

### 写入新知识（Python）

```python
import os
from pathlib import Path
from datetime import date

kb = Path(os.environ['KNOWLEDGE_BASE_DIR'])

# 写入临时文件（读后需删）
target = kb / 'temp' / 'my-analysis.md'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(
    f'---\nexpires: {date.today().isoformat()}\n---\n\n# My Analysis\n\n内容...',
    encoding='utf-8'
)

# 存档（code review 报告命名规范）
report_date = date.today().isoformat()
change_num = "12345"
report = kb / 'code-review' / f'{report_date}_{change_num}.md'
report.write_text('# Code Review 报告\n\n...', encoding='utf-8')
```

### 追加到现有文件（幂等保护）

```python
target = kb / 'troubleshooting' / 'gerrit-ssh.md'
if target.exists():
    existing = target.read_text(encoding='utf-8')
    if "connection refused" not in existing:  # 检查内容是否已存在
        target.write_text(existing + '\n\n## 新增章节\n内容...', encoding='utf-8')
else:
    target.write_text('# Gerrit SSH 问题\n\n内容...', encoding='utf-8')
```

---

## 四、多 Agent 协作模式

### 模式 A：生产者 → 消费者（通过 temp/）

适用于：Agent A 完成任务后，Agent B 读取结果。

```
Agent A（code-review-agent）：
  1. 执行 code review
  2. 写入 kb://temp/review-12345.md（含 expires 字段）

Agent B（报告汇总 agent）：
  1. memory_search "temp review"
  2. 读取 kb://temp/review-12345.md
  3. 写入 kb://code-review/2024-01-15_12345.md（存档）
  4. 删除 kb://temp/review-12345.md
```

### 模式 B：共享上下文（通过 architecture/）

适用于：多个 Agent 共享系统设计文档。

```
任何 Agent：
  - 读取 kb://architecture/service-layer.md 了解系统结构
  - 更新时写入同一文件（先读后写，避免覆盖）
```

### 模式 C：Agent 私有目录

每个 Agent 可在 `{agent_def_dir}/` 下维护自己的私有上下文。

```
code-review-agent/context.md       → code-review agent 的运行状态
gerrit-monitor-agent/queue.md      → gerrit 监听 agent 的待处理队列
```

---

## 五、文件命名规范快速参考

| 场景 | 命名格式 | 示例 |
|---|---|---|
| Code review 报告（存档） | `YYYY-MM-DD_<change>.md` | `2024-01-15_12345.md` |
| 问题记录 | `<topic>-issue.md` | `gerrit-connection-issue.md` |
| 架构文档 | `<component>-design.md` | `notification-service-design.md` |
| 临时文件 | 无特定格式，需含 expires 字段 | `temp-analysis.md` |
| Agent 上下文 | `<agent-name>/context.md` | `code-review-agent/context.md` |

---

## 六、写入前检查清单

在将内容写入知识库之前执行：

- [ ] 文件名使用小写英文 + 连字符（无空格、无下划线、无大写）
- [ ] 文件扩展名为 `.md`
- [ ] 目录深度不超过 2 层（如 `category/file.md`）
- [ ] 不包含密码、API token、内网 IP、私钥等敏感信息
- [ ] temp/ 目录中的文件包含 `expires: YYYY-MM-DD` 头部
- [ ] 如目标文件已存在，先读取再决定追加或更新（不覆盖）
- [ ] 文件大小 ≤ 1 MB（超过时考虑拆分）
