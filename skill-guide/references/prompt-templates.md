# Prompt Templates & Reference Templates (规范 9–10)

> **来源：** 本文档是 skill-guide 的模板库。使用 skill-guide PART 2 时参考。

<a name="rule-9"></a>
### 规范 9：模板与参考（非脚本操作）

**原则：** 凡是需要模型自行执行的命令、代码片段或配置，必须在 SKILL.md 中提供**完整可用的模板或示例**，不能仅靠自然语言描述让模型自行生成。

#### 9.1 何时提供模板

| 操作类型 | 要求 |
|----------|------|
| shell 命令 | 完整命令，用 `<占位符>` 标注需要替换的部分 |
| 配置文件 | 提供 `.example` 文件 + 关键字段说明表 |
| 代码片段（Python/JS 等） | 提供完整可运行片段，含 import 和入口 |
| API 请求 Body | 提供完整 JSON 示例 + Schema 表 |
| 正则表达式 | 提供表达式 + 至少 2 个匹配示例和 1 个不匹配示例 |

#### 9.2 模板格式规范

模板中需替换的占位符统一使用 `<大写下划线>` 格式，并在模板后附说明表：

````markdown
**命令模板：**
```bash
python3 "$SKILL_DIR/scripts/review_job.py" \
  --workspace "<WORKSPACE_PATH>" \
  --project "<GERRIT_PROJECT_NAME>" \
  --max-events <MAX_EVENTS>
```

**占位符说明：**

| 占位符 | 示例值 | 说明 |
|--------|--------|------|
| `<WORKSPACE_PATH>` | `/home/user/myproject` | 绝对路径，对应 WORKSPACE |
| `<GERRIT_PROJECT_NAME>` | `platform/frameworks/base` | Gerrit 中的项目名，区分大小写 |
| `<MAX_EVENTS>` | `10` | 每次运行处理的最大事件数，整数，默认 10 |
````

#### 9.3 配置示例规范

env-var-only skills 不需要 `config.json.example`；若 skill 需要复杂配置，提供 `.env.example` 文件并附字段说明表。

- env-var-only skill：在 SKILL.md 中列出环境变量名称、类型、是否必填、默认值和说明（见规范 7.5）
- 需要复杂配置的 skill：提供 `.env.example`，其中占位符值使用 `<FIELD_NAME>` 格式
- 示例文件必须是合法格式（`.env` 不含 shell 专属语法，JSON 示例不含注释）
- SKILL.md 中必须有对应字段说明表（见规范 7.5）

```dotenv
GERRIT_HOST=<GERRIT_HOST>
GERRIT_PORT=29418
GERRIT_HTTP_PORT=8080
GERRIT_USERNAME=<GERRIT_USERNAME>
HTTP_PASSWORD=<HTTP_PASSWORD>
REVIEW_TEST_MODE=true
PROJECT_FILTER=
```

---

<a name="rule-10"></a>
### 规范 10：Prompt 模板（限制模型自由操作空间）

**原则：** 对于需要模型在特定 agent 平台（如 OpenClaw）执行的复杂操作，SKILL.md 必须提供**直接可用的 prompt 模板**，让模型只需填入少量参数即可，而不是自行理解并生成操作。

**目标：** 减少模型理解偏差，确保弱模型在执行 skill 时的行为与预期一致。

#### 10.1 何时提供 Prompt 模板

凡是以下类型的操作，必须提供 prompt 模板：

| 操作类型 | 说明 |
|----------|------|
| 建立定时任务（cron / scheduler）| 不同平台设置方式差异大，必须给模板 |
| 启动/停止后台进程 | 涉及 PID 管理、重启逻辑 |
| 发送消息到指定会话/频道 | 消息格式和目标选择容易出错 |
| 调用另一个 skill | 需要精确的 skill 名称和参数格式 |
| 多步骤需要上下文传递 | 中间结果如何传给下一步 |

#### 10.2 Prompt 模板格式

在 SKILL.md 中，用固定格式给出每种平台的 prompt 模板：

````markdown
### Prompt 模板：[操作名称]

> **适用平台：** OpenClaw / 通用 cron / Windows 任务计划程序

**[平台名] Prompt：**

```
<直接粘贴给模型的 prompt，含占位符>
```

**占位符说明：**

| 占位符 | 示例值 | 说明 |
|--------|--------|------|
| `<PLACEHOLDER>` | `example` | 说明 |
````

#### 10.3 常用 Prompt 模板示例

**示例 A：OpenClaw — 建立定时任务（cron job）**

````markdown
### Prompt 模板：OpenClaw 建立定时 cron job

**OpenClaw Prompt：**

```
请为我建立一个每 <INTERVAL> 分钟运行一次的定时任务，执行以下操作：

1. 运行脚本: python3 "<SKILL_DIR>/scripts/<SCRIPT_NAME>.py" --workspace "<WORKSPACE_PATH>"
2. 将脚本的 stdout 输出作为输入，继续执行以下步骤：
   <STEPS_DESCRIPTION>
3. 如果脚本 exit code 为 1，停止本次任务并在聊天中显示错误信息（来自 stderr）。
4. 如果脚本 exit code 为 2，<SPECIAL_CASE_HANDLING>

定时任务建立后，请确认任务已注册，并告知下次运行时间。
```

**占位符说明：**

| 占位符 | 示例值 | 说明 |
|--------|--------|------|
| `<INTERVAL>` | `1` | 运行间隔（分钟），整数 |
| `<SKILL_DIR>` | `/home/user/.agents/skills/agent-code-review` | skill 安装目录绝对路径 |
| `<SCRIPT_NAME>` | `review_job` | 脚本文件名（不含 .py） |
| `<WORKSPACE_PATH>` | `/home/user/myproject` | 项目工作目录绝对路径 |
| `<STEPS_DESCRIPTION>` | 见下方业务说明 | 模型在读取 JSON 输出后要执行的动作 |
| `<SPECIAL_CASE_HANDLING>` | `将输出打印到当前会话` | exit code 2 的特殊处理逻辑 |
````

**示例 B：OpenClaw — 检查进程存活并在必要时重启**

````markdown
### Prompt 模板：OpenClaw 检查并重启后台进程

**OpenClaw Prompt：**

```
请检查以下后台进程是否在运行，如果没有则重新启动：

检查步骤（跨平台，使用 Python）：
  1. 运行以下 Python 脚本检查进程状态：

     python3 "<SKILL_DIR>/scripts/check_listener.py" --pid-file "<WORKSPACE_PATH>/<PID_FILENAME>"

     （Windows 用 python 代替 python3）

  2. 如果脚本输出 "status: running"，无需操作。
  3. 如果脚本输出 "status: dead" 或 "status: missing"，执行以下命令启动进程：

     python3 "<SKILL_DIR>/scripts/<SCRIPT_NAME>.py" --workspace "<WORKSPACE_PATH>" <EXTRA_ARGS>

  4. 启动后，将新进程 PID 写入 "<WORKSPACE_PATH>/<PID_FILENAME>"

完成后告知进程状态（running / restarted / failed）。
```

> **注意：** check_listener.py 必须是跨平台的 Python 脚本（stdlib os.getpid() 或 psutil 可选），
> 不得在 prompt 中直接使用 `kill -0`（Linux only）或 `tasklist`（Windows only）。

**占位符说明：**

| 占位符 | 示例值 | 说明 |
|--------|--------|------|
| `<WORKSPACE_PATH>` | `/home/user/myproject` | 项目工作目录绝对路径 |
| `<PID_FILENAME>` | `gerrit_listener.pid` | PID 文件名 |
| `<SKILL_DIR>` | `/home/user/.agents/skills/gerrit-api` | skill 安装目录绝对路径 |
| `<SCRIPT_NAME>` | `gerrit_stream_events` | 脚本文件名（不含 .py） |
| `<EXTRA_ARGS>` | `--output events.jsonl --reconnect` | 额外命令行参数 |
````

**示例 C：OpenClaw — 发送报告到指定会话（test_mode）**

````markdown
### Prompt 模板：OpenClaw 发送 Code Review 报告到会话

**OpenClaw Prompt（exit code 为 2 时使用）：**

```
脚本已完成分析，请将以下 Code Review 报告发送到会话 "<SESSION_ID>"：

<REPORT_CONTENT>

发送后无需等待回复，继续下一次定时任务。
```

**占位符说明：**

| 占位符 | 示例值 | 说明 |
|--------|--------|------|
| `<SESSION_ID>` | `session-abc123` | 目标会话 ID（从配置或用户输入获取）|
| `<REPORT_CONTENT>` | （脚本 stdout 内容）| 直接插入脚本输出的报告文本 |
````

#### 10.4 Prompt 模板使用原则

1. **每个 prompt 模板必须标注"适用平台"**（OpenClaw / 通用 / Windows 等）
2. **占位符必须有说明表**，不能让模型自行猜测含义
3. **模板不能包含歧义判断**，即不能有"根据情况决定"等模糊说法
4. **提供至少一个完整填写后的示例**（将所有占位符替换为实际值）

**完整示例（填写后）：**

```
请为我建立一个每 1 分钟运行一次的定时任务，执行以下操作：

1. 运行脚本: python3 "/home/user/.agents/skills/agent-code-review/scripts/review_job.py" --workspace "/home/user/myproject"
2. 将脚本的 stdout 输出（JSON 格式）解析后，对其中 events 数组的每个条目进行 code review。
3. 如果脚本 exit code 为 1，停止本次任务并在聊天中显示错误信息（来自 stderr）。
4. 如果脚本 exit code 为 2，表示 test_mode，将审查报告打印到当前会话。

定时任务建立后，请确认任务已注册，并告知下次运行时间。
```

---
