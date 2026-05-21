# Code Review Workflow & Report Format

> **来源：** code-review skill 参考文件。执行 code review 时的详细步骤和报告模板。

### 阶段一 — 解析输入，提取 change_number

根据收到的信息类型，提取 `change_number`（Gerrit 变更的数字 ID）：

| 输入类型 | 提取方法 |
|---|---|
| Gerrit 页面 URL | 从 URL 中提取数字：`/c/proj/+/NUMBER` 或 `#/c/NUMBER` |
| 纯数字 | 直接使用，格式正则：`^\d+$` |
| Change-Id | 格式正则：`^I[0-9a-f]{40}$`，需通过 query 命令查找对应 change number（见下方） |
| Commit SHA | 格式正则：`^[0-9a-f]{7,40}$`，需通过 query 命令查找（见下方） |
| Stream event JSON | 读取 `change.number` 字段；`patchSet.revision` 字段为 commit SHA |

**URL 提取示例：**
```
https://gerrit.example.com/c/platform/frameworks/base/+/12345      → 12345
https://gerrit.example.com/c/platform/frameworks/base/+/12345/2    → 12345（patchset 2）
https://gerrit.example.com/#/c/12345/                              → 12345
```

**通过 Change-Id 查询 change number：**
```bash
python3 .agents/skills/gerrit-api/scripts/gerrit_api.py \
  query "change:Iabcdef1234567890abcdef1234567890abcdef12+limit:1"
```

**通过 commit SHA 查询 change number：**
```bash
python3 .agents/skills/gerrit-api/scripts/gerrit_api.py \
  query "commit:abc123def456+limit:1"
```

---

### 阶段二 — 通过 gerrit-api 获取 Patch 数据

以下命令全部使用 `gerrit-api` skill 的脚本（路径: `.agents/skills/gerrit-api/scripts/`）。

#### 2A — 获取变更详情

```bash
python3 .agents/skills/gerrit-api/scripts/gerrit_api.py get-change <change_number>
```

**从输出中提取：**
- `subject` — 提交标题
- `project` — 项目名
- `branch` — 目标分支
- `owner.username` 或 `owner.name` — 提交者
- `current_revision` — 当前 patchset 的 commit SHA（后续步骤需要）

#### 2B — 列出变更文件

```bash
python3 .agents/skills/gerrit-api/scripts/gerrit_api.py list-files <change_number>
```

输出为文件路径列表。跳过以下文件（对应 `skip_file_patterns` 配置）：
- 配置文件（如 `*.json`, `*.xml`, `*.yaml`）按 `skip_file_patterns` 跳过

#### 2C — 获取每个文件的 Diff

对 `list-files` 返回的每个文件路径执行：

```bash
python3 .agents/skills/gerrit-api/scripts/gerrit_api.py \
  get-diff <change_number> "path/to/file.java"
```

**Windows 将 `python3` 替换为 `python`，路径分隔符用 `%`：**
```batch
python .agents\skills\gerrit-api\scripts\gerrit_api.py get-diff <change_number> "path/to/file.java"
```

收集所有文件的 diff 后，进入阶段三。

---

### 阶段三 — Code Review（对所有收集到的 diff）

加载 **T2MCodingRule** skill，按以下步骤审查。

#### Checklist: 审查前准备

- [ ] `get-change` 已成功，已知 `subject`、`project`、`branch`、`current_revision`
- [ ] `list-files` 已返回文件列表（过滤掉 `skip_file_patterns` 中的文件）
- [ ] 所有文件的 `get-diff` 已完成
- [ ] T2MCodingRule skill 已加载

#### 3A — 提交信息（Commit Message）审查

依据 **T2MCodingRule 一、Git Commit Message 规范**逐条检查：

| 编号    | 检查项                                  | 正则 / 规则                                                                                      | 问题级别       |
| ----- | ------------------------------------ | -------------------------------------------------------------------------------------------- | ---------- |
| CM-1  | 首行格式：`<Issue Key> <Summary>` 或 `[<Issue Key>] <Summary>` | 首行必须匹配 `^(\[?[A-Z0-9]+-\d+\]?)\s+\S+.*`；Issue Key 可带或不带中括号，均视为合法 | 🟠 ERROR   |
| CM-2  | Issue Key 格式                         | `^\[?[A-Z0-9]+-\d+\]?`；带括号形式（`[FPS-100]`）与不带括号形式（`FPS-100`）均合法           | 🟡 WARNING |
| CM-3  | 首行与正文之间有空行                           | 第 2 行须为空行（如有正文）                                                                              | 🟠 ERROR   |
| CM-4  | 包含 `* Root Cause` 字段                 | 正文中存在 `^\* Root Cause`                                                                       | 🟠 ERROR   |
| CM-5  | 包含 `* Solution` 字段                   | 正文中存在 `^\* Solution`                                                                         | 🟠 ERROR   |
| CM-6  | 包含 `* Test Steps` 字段                 | 正文中存在 `^\* Test Steps`                                                                       | 🟠 ERROR   |
| CM-7  | 包含 `* Test Result` 字段                | 正文中存在 `^\* Test Result`                                                                      | 🟠 ERROR   |
| CM-8  | `* Solution` 描述具体技术改动                | 内容不得为泛化表述（如 "Fix code"、"代码优化"、"按要求修改"）；正则排除：`(?i)(fix code\|代码优化\|按.*要求\|meet.*requirement)` | 🟠 ERROR   |
| CM-9  | 涉及安全变更时有 `* Security Check` 字段       | 若 diff 含安全相关改动，需检查是否包含 `^\* Security Check`                                                  | 🟡 WARNING |
| CM-10 | 涉及兼容性变更时有 `* Compatibility Check` 字段 | 若 diff 含接口/API 改动，需检查是否包含 `^\* Compatibility Check`                                          | 🟡 WARNING |
| CM-11 | 涉及 AOSP 框架/系统服务/架构变更时引用 ADR          | commit message 中包含 ADR 文档引用                                                                  | 🔵 INFO    |

> **注意：** `get-change` 返回的 `subject` 字段仅为首行。如需检查完整 commit message，可在报告中注明"无法获取完整 message"并仅基于 subject 审查 CM-1 ~ CM-3。

#### 3B — 文件 Diff 审查

**只审查 diff 中新增/修改的行（`+` 开头的行）**，根据扩展名选择规范：

| 扩展名 | 规范 |
|---|---|
| `.java` | T2MCodingRule 四（Java 编码规范）|
| `.c`, `.h` | T2MCodingRule 五（C 编码规范）|
| `.cpp`, `.cc`, `.hpp` | T2MCodingRule 六（C++ 编码规范）|
| 其他 | 通用质量检查 |

审查重点：
- [ ] 命名规范（类/变量/函数）
- [ ] 注释完整性（公共 API、复杂逻辑）
- [ ] 安全规范（T2MCodingRule 七）：无硬编码密码、日志无敏感信息
- [ ] 兼容性规范（T2MCodingRule 八）：无废弃 API、接口向后兼容
- [ ] 逻辑错误、资源泄漏、死锁风险

#### 3C — 问题定级与 PASS/FAIL 判断

| 级别 | 说明 | 影响结果 |
|---|---|---|
| 🔴 CRITICAL | 编译错误、安全漏洞、严重数据风险 | 导致 FAIL |
| 🟠 ERROR | 违反 T2MCodingRule 强制规则 | 导致 FAIL |
| 🟡 WARNING | 建议改进、风格问题 | 不影响 PASS/FAIL |
| 🔵 INFO | 可选建议 | 不影响 PASS/FAIL |

**判断：** 有任意 🔴 或 🟠 → **FAIL**，否则 **PASS**。

#### 3D — 生成报告（固定格式）

> ⚠️ **严格按以下格式输出报告，不允许附加任何格式外的内容。**

```
**PASS** 或 **FAIL**

| 级别 | 文件 | 问题 |
|---|---|---|
| 🔴 CRITICAL | {file}:{line} | [{编号}] {一句话描述，≤30字} |
| 🟠 ERROR | commit-message:1 | [CM-1] 首行缺少有效 Issue Key |
| 🟡 WARNING | {file}:{line} | [{编号}] {描述，≤30字} |
| 🔵 INFO | {file}:{line} | {描述，≤30字} |

# Patch信息
URL: {gerrit_url}/c/{project}/+/{change_number}
Change-Id: {change_id}
Owner: {owner_email}
Repo: {project}
Branch: {branch}

# 问题清单
## {file_path}:{line}
[{级别}] [{编号}]{问题描述}
- **原因:** {违反的规范条目及理由}
- **建议:** {具体修改建议}
```

**格式规则（严格执行）：**
- 第一行必须是 `**PASS**` 或 `**FAIL**`
- 无问题时，问题列表表格省略
- `# Patch信息` 必须包含 URL、Change-Id、Owner、Repo、Branch 五个字段
- `# 问题清单` 每个问题以 `## {文件}:{行号}` 为标题（commit message 使用 `## commit-message:1`）
- 每个问题必须有 `- **原因:**` 和 `- **建议:**` 两行
- 问题描述不超过 30 字；规范编号（CM-1 等）在描述头部标出

**示例（FAIL）：**

```
**FAIL**

| 级别 | 文件 | 问题 |
|---|---|---|
| 🟠 ERROR | commit-message:1 | [CM-1] 首行格式不符合 `<Issue Key> <Summary>` |
| 🔴 CRITICAL | generic/vendor/common/init.te:13 | 允许写 /proc/sysrq-trigger |

# Patch信息
URL: https://gerrit.t2mobile.com/c/quicl/vendor/fairphone/source/apps/+/129616
Change-Id: Ibc9288f7fbe0bb3295693f417ff6b70aac240de4
Owner: tianwen.zhang@t2mobile.com
Repo: quicl/vendor/fairphone/source/apps
Branch: 635_17x_qssi_dev

# 问题清单
## commit-message:1
[🟠 ERROR] [CM-1]首行格式不符合：`<Issue Key> <Summary>`
- **原因:** 首行必须匹配 `^\S+\s+\S+.*`，即 Issue Key + 空格 + Summary
- **建议:** 修改为 `[FP6A17-138] add tcpdump function[2/3]`

## generic/vendor/common/init.te:13
[🔴 CRITICAL] 允许写 /proc/sysrq-trigger（proc_sysrq:file write）
- **原因:** 新增 `allow vendor_init proc_sysrq:file w_file_perms;` 允许写入 /proc/sysrq-trigger，可能触发系统级 sysrq 操作被滥用。
- **建议:** 仅在明确受信流程中允许；限制可触发的命令集合、在实现层加入白名单并记录审计日志。
```

**示例（PASS）：**

```
**PASS**

# Patch信息
URL: https://gerrit.example.com/c/myproject/+/12345
Change-Id: Iabcdef1234567890abcdef1234567890abcdef12
Owner: john.doe@example.com
Repo: myproject
Branch: main

# 问题清单
（无问题）
```
