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
| CM-1  | 首行格式：`<Issue Key> <Summary>`         | 首行必须匹配 `^\S+\s+\S+.*`，即 Issue Key + 空格 + Summary                                             | 🟠 ERROR   |
| CM-2  | Issue Key 格式                         | `^\[?[A-Z0-9]+-\d+\]?`                                                                       | 🟡 WARNING |
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

> ⚠️ **严格按以下格式输出报告，不得附加任何格式外的文字、解释、前言或后记。**

```
============================
Code Review 报告
============================
变更：#{change_number} — {subject}
项目：{project}  分支：{branch}
提交人：{uploader}
审查结果：【PASS】 或 【FAIL】
============================

## 提交信息审查

[{级别}] {CM编号} {问题描述}
→ 原因：{违反的规范条目，如 "T2MCodingRule 1.3: Solution 字段描述不具体"}
→ 建议：{具体修改建议}

（无问题时写 "✅ 符合规范"）

## 文件审查

### {file_path}
[{级别}] 行 {line}: {问题描述}
→ 原因：{违反的规范条目}
→ 建议：{具体修改建议}

（无问题时写 "✅ 无问题"）

============================
汇总：🔴 {n}  🟠 {n}  🟡 {n}  🔵 {n}
============================
```

**级别标记说明：**

| 写法 | 含义 |
|---|---|
| `[🔴 CRITICAL]` | 安全漏洞、编译错误 |
| `[🟠 ERROR]` | 违反强制规则 |
| `[🟡 WARNING]` | 建议改进 |
| `[🔵 INFO]` | 可选建议 |

**报告输出规则（严格执行）：**
- 报告以第一行 `============================` 开始，以最后一行 `============================` 结束
- 报告正文以外**不得输出任何其他内容**（无引言、无总结段落、无 markdown 代码块包裹）
- `## 提交信息审查` 和 `## 文件审查` 两节均必须存在，不得省略
- 每个问题项必须包含 `→ 原因` 和 `→ 建议` 两行

---

### 阶段四 — 发布结果

读取 `CODE_REVIEW_TEST_MODE` 环境变量（默认 `true`）：

#### 4A — CODE_REVIEW_TEST_MODE = true（默认）

直接将报告打印到当前会话，**不操作 Gerrit**。

#### 4B — CODE_REVIEW_TEST_MODE = false

用 gerrit-api 发布 review comment 并设置 Verified 标签：

```bash
# PASS：Verified=0，发布 comment
python3 .agents/skills/gerrit-api/scripts/gerrit_api.py \
  review <change_number> current \
  '{"message": "<报告文本>", "labels": {"Verified": 0}, "tag": "code-review-agent"}'

# FAIL：Verified=-1，发布 comment
python3 .agents/skills/gerrit-api/scripts/gerrit_api.py \
  review <change_number> current \
  '{"message": "<报告文本>", "labels": {"Verified": -1}, "tag": "code-review-agent"}'
```

**报告文本较长时（推荐），先写文件再传入：**

```bash
# 将报告写入临时文件
python3 -c "
import sys, json
report = '''
{报告文本}
'''.strip()
print(json.dumps({'message': report, 'labels': {'Verified': 0}, 'tag': 'code-review-agent'}))
" > review_body.json

python3 .agents/skills/gerrit-api/scripts/gerrit_api.py \
  review <change_number> current "$(cat review_body.json)"
```

```powershell
# Windows PowerShell
$body = @{
    message = @"
{报告文本}
"@
    labels  = @{ Verified = 0 }
    tag     = "code-review-agent"
} | ConvertTo-Json -Compress

python .agents\skills\gerrit-api\scripts\gerrit_api.py review <change_number> current $body
```

**gerrit-api review 命令退出码：**

| 退出码 | 含义 | 后续动作 |
|---|---|---|
| `0` | 成功提交到 Gerrit | 完成 |
| 非 0 | 提交失败（详见 stderr）| 检查权限或网络 |

---
