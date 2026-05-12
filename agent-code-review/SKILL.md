---
name: agent-code-review
description: >
  Code review automation skill. The agent monitors Gerrit stream events,
  fetches patch diffs for new patchsets, reviews them against T2Mobile
  coding standards (T2MCodingRule), generates a structured Chinese review
  report (PASS/FAIL), and—when not in test mode—posts the report as a
  Gerrit comment and sets Verified=-1 on failure.
dependencies:
  - gerrit-api
  - T2MCodingRule
compatibility: Requires python3 (≥3.9). No extra pip packages needed.
---

# Agent Code Review Skill

**功能概述：** 自动化 Code Review。Agent 持续监听 Gerrit 事件流，对每个新提交（patchset-created）按 T2Mobile 编码规范进行审查，生成中文报告，并（非测试模式下）将结果写回 Gerrit。

**依赖 Skill：**
- `gerrit-api` — 访问 Gerrit REST API / SSH 事件流
- `T2MCodingRule` — T2Mobile 编码规范知识库（审查标准来源）

**本 skill 脚本（stdlib only，无需 pip）：**
- `scripts/poll_events.py` — 原子读取事件队列，拉取 patch diff，输出 JSON 供 Agent 审查
- `scripts/post_review.py` — 向 Gerrit 提交 review comment，可设置 Verified 标签
- `scripts/ensure_stream_listener.py` — 健康检查 + 自动重启 Gerrit 事件监听进程

---

## ⚠️ Step 0 — 初始化环境变量（每次会话执行一次）

### Step 0A — 记录 Workspace

> `SKILL_WORKSPACE` 是 agent 的项目目录，用于查找配置文件和存放输出文件。

```bash
# Linux / macOS / Git Bash
export SKILL_WORKSPACE="$(pwd)"

# Windows CMD
set SKILL_WORKSPACE=%CD%

# Windows PowerShell
$env:SKILL_WORKSPACE = (Get-Location).Path
```

### Step 0B — 确认本 Skill 安装目录（SKILL_DIR）

> `SKILL_DIR` 是本 skill (`agent-code-review`) 的安装目录，**不同于** `SKILL_WORKSPACE`。

```bash
# Linux / macOS — 自动检测并设置 SKILL_DIR
export SKILL_DIR=$(python3 -c "
import os, sys
from pathlib import Path
name = 'agent-code-review'
ws = Path(os.environ.get('SKILL_WORKSPACE', os.getcwd()))
for p in [ws/'.agents'/'skills'/name, Path.home()/'.agents'/'skills'/name]:
    if p.is_dir():
        print(p); sys.exit(0)
sys.exit(1)
") || {
    echo "ERROR: agent-code-review skill not found."
    echo "Install: npx skills add https://github.com/vancebs/skills --skill agent-code-review"
}

# Windows PowerShell
$skillName = 'agent-code-review'
$env:SKILL_DIR = @(
    "$env:SKILL_WORKSPACE\.agents\skills\$skillName",
    "$HOME\.agents\skills\$skillName"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
```

之后脚本调用始终使用：
```bash
python3 "$SKILL_DIR/scripts/poll_events.py" --workspace "$SKILL_WORKSPACE"
```

---

## ✅ 初始化配置清单（一次性，首次使用前完成）

### Step 1 — 检查依赖 Skill

#### gerrit-api

```bash
# 检测 gerrit-api 是否已安装
python3 -c "
import os
from pathlib import Path
ws = Path(os.environ.get('SKILL_WORKSPACE', os.getcwd()))
for p in [ws/'.agents'/'skills'/'gerrit-api', Path.home()/'.agents'/'skills'/'gerrit-api']:
    if p.is_dir():
        print('OK:', p); exit(0)
print('NOT FOUND')
"
```

若未安装：
```bash
npx skills add https://github.com/vancebs/skills --skill gerrit-api
```

安装后，按 **gerrit-api/SKILL.md** 的 Setup Checklist 完成配置（设置 Gerrit 凭据、测试连接）。

> **注意：** 使用 gerrit-api 的功能时，请按照 gerrit-api skill 的 SKILL.md 操作，不要直接引用 gerrit-api 脚本的绝对路径。gerrit-api 的 `SKILL_DIR` 应按照 gerrit-api/SKILL.md 的 Step 0B 独立检测。

#### T2MCodingRule

T2MCodingRule 无需额外配置，加载 skill 即可。

```bash
# 检测 T2MCodingRule 是否已安装
python3 -c "
import os
from pathlib import Path
ws = Path(os.environ.get('SKILL_WORKSPACE', os.getcwd()))
for p in [ws/'.agents'/'skills'/'T2MCodingRule', Path.home()/'.agents'/'skills'/'T2MCodingRule']:
    if p.is_dir():
        print('OK:', p); exit(0)
print('NOT FOUND')
"
```

若未安装：
```bash
npx skills add https://github.com/vancebs/skills --skill T2MCodingRule
```

### Step 2 — 创建 agent-code-review 配置文件

```bash
# Linux / macOS
mkdir -p "$SKILL_WORKSPACE/config/agent-code-review"
cp "$SKILL_DIR/scripts/agent_code_review_config.json.example" \
   "$SKILL_WORKSPACE/config/agent-code-review/agent_code_review_config.json"
```

编辑配置文件内容：

```json
{
  "test_mode": true,
  "events_file": "/absolute/path/to/events.jsonl",
  "outbox_file": "",
  "review_projects": [],
  "review_branches": [],
  "skip_file_patterns": []
}
```

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `test_mode` | `true` | **true** = 仅输出报告到会话，不写 Gerrit；**false** = 发布到 Gerrit |
| `events_file` | `{workspace}/events.jsonl` | 事件队列文件路径（绝对路径） |
| `outbox_file` | `""` | 异常备份文件（留空用默认） |
| `review_projects` | `[]` | 只审查指定项目（空数组 = 全部） |
| `review_branches` | `[]` | 只审查指定分支（空数组 = 全部） |
| `skip_file_patterns` | `[]` | 跳过匹配此 glob 的文件（如 `["*.md", "*.xml"]`） |

> ⚠️ 将配置文件加入 `.gitignore`：
> ```
> config/agent-code-review/agent_code_review_config.json
> ```

### Step 3 — 测试 Gerrit 连接

使用 gerrit-api skill 验证连接（按照 gerrit-api/SKILL.md 的操作方法）。

### Step 4 — 配置 Cron Job（定时触发健康检查 + Code Review）

Cron Job 是整个方案的入口。它每 1 分钟执行一次，完成两件事：
1. **确保事件流监听进程在运行**（如已停止则自动重启）
2. **读取队列并执行 Code Review**（如有事件）

**首选：使用 OpenClaw 原生 Cron Job**

在 OpenClaw 中创建 cron job，间隔 1 分钟，任务内容：

```
执行 agent-code-review 工作流（见下方"工作流"章节）
```

**备选：Python 后台轮询**（平台不支持 cron 时使用）

```bash
python3 - <<'EOF' &
import time, subprocess, os, sys
workspace = os.environ.get("SKILL_WORKSPACE", os.getcwd())
skill_dir = os.environ.get("SKILL_DIR", "")
while True:
    time.sleep(60)
    # 每次循环执行健康检查 + review（等同于 cron job）
    subprocess.run([sys.executable,
        skill_dir + "/scripts/ensure_stream_listener.py",
        "--workspace", workspace])
    subprocess.run([sys.executable,
        skill_dir + "/scripts/poll_events.py",
        "--workspace", workspace])
EOF
echo "Background poller PID: $!"
```

---

## 📋 工作流：Code Review（每次 Cron 触发时执行）

> 以下是 Agent 每次被 cron 触发后应依次执行的完整步骤。

### 阶段一 — 健康检查：确保事件流监听进程在运行

```bash
python3 "$SKILL_DIR/scripts/ensure_stream_listener.py" \
  --workspace "$SKILL_WORKSPACE"
```

**执行逻辑：**
1. 读取 PID 文件 `{workspace}/gerrit_stream_listener.pid`
2. 如果 PID 对应进程仍在运行 → 输出"已运行"，直接返回（exit 0）
3. 如果进程已停止或 PID 文件不存在：
   - 自动查找 gerrit-api skill 安装目录（按 `GERRIT_API_SKILL_DIR` env var → workspace-local → 全局）
   - 启动 `gerrit_stream_events.py`（参数：`--output {events_file} --filter patchset-created --reconnect --pid-file ...`）
   - 返回 exit 0（已重启）或 exit 2（未找到 gerrit-api skill）

**如果返回 exit 2**（gerrit-api 未安装）：
- 停止本次执行
- 按 Step 1 安装并配置 gerrit-api skill

**（可选）手动指定 gerrit-api 目录：**
```bash
# 设置 GERRIT_API_SKILL_DIR 避免自动检测失败
export GERRIT_API_SKILL_DIR="$SKILL_WORKSPACE/.agents/skills/gerrit-api"

python3 "$SKILL_DIR/scripts/ensure_stream_listener.py" \
  --workspace "$SKILL_WORKSPACE"
```

---

### 阶段二 — 读取事件队列

```bash
python3 "$SKILL_DIR/scripts/poll_events.py" \
  --workspace "$SKILL_WORKSPACE" \
  > /tmp/review_payload.json
```

输出为 JSON，结构如下：

```json
{
  "test_mode": true,
  "events": [
    {
      "change_id": 12345,
      "project": "myOrg/myRepo",
      "branch": "main",
      "subject": "Fix login bug",
      "commit_msg": "Fix login bug\n\nChange-Id: I...",
      "revision": "abc123",
      "received_at": "2026-05-12T06:00:00Z",
      "event_summary": "patchset-created by john.doe on myOrg/myRepo#12345",
      "files": [
        {
          "path": "src/main/java/com/example/LoginService.java",
          "status": "M",
          "diff_text": "- old line\n+ new line\n..."
        }
      ]
    }
  ]
}
```

- **如果 `events` 为空** → 本次无新提交，结束。
- **如果某个 event 有 `error` 字段** → 检查 gerrit-api 配置；见故障排查章节。

---

### 阶段三 — 逐事件 Code Review

对 `events` 中每一条记录，执行以下审查：

#### 3A — 提交信息（Commit Message）检查清单

- [ ] 格式符合 T2MCodingRule 一：`type(scope): subject`
- [ ] `type` 为规范值之一（feat/fix/refactor/docs/test/chore/style/perf）
- [ ] `subject` 不超过 50 字符，不以句号结尾
- [ ] Body 中包含 Jira ID（如 `Issue: PROJ-123`）
- [ ] 如有 Breaking Change，有 `BREAKING CHANGE:` 行

#### 3B — 每个文件的 Diff 审查

**判断语言并选择标准：**

| 文件扩展名 | 适用规范 |
|---|---|
| `.java` | T2MCodingRule 四（Java 编码规范） |
| `.c`, `.h` | T2MCodingRule 五（C 编码规范） |
| `.cpp`, `.cc`, `.hpp` | T2MCodingRule 六（C++ 编码规范） |
| 其他 | 通用代码质量标准（见 3C） |

**Java/C/C++ 核心检查项：**

- [ ] **命名规范**：类/变量/函数命名符合 T2M 规范？
- [ ] **注释规范**：公共 API / 复杂逻辑有必要注释？
- [ ] **安全规范**（T2MCodingRule 七）：
  - [ ] 无硬编码密码、密钥、token
  - [ ] 日志中无敏感信息明文输出
  - [ ] 权限检查正确（Android 相关）
- [ ] **兼容性规范**（T2MCodingRule 八）：
  - [ ] 无使用 `@Deprecated` API
  - [ ] HAL / AIDL 接口修改向后兼容
- [ ] **代码逻辑**：明显错误、资源泄漏、死锁风险？

**问题定级：**

| 级别 | 说明 | 对结果影响 |
|---|---|---|
| 🔴 CRITICAL | 编译错误、安全漏洞、严重数据风险 | 导致 FAIL |
| 🟠 ERROR | 违反 T2MCodingRule 强制规则 | 导致 FAIL |
| 🟡 WARNING | 建议改进、非 T2M 覆盖语言问题 | 不影响结果 |
| 🔵 INFO | 风格建议、可选优化 | 不影响结果 |

#### 3C — 非 T2M 覆盖语言（通用质量审查）

- 命名混乱（无意义变量名）→ 🟡 WARNING
- 重复代码块 → 🟡 WARNING
- 函数过长（>100 行）→ 🟡 WARNING
- 编译错误（如语法错误）、安全凭证硬编码、SQL 注入等 → 升级为 🔴 CRITICAL

---

### 阶段四 — 生成 Review 报告

按以下格式生成报告（纯文本）：

```
============================
Code Review 报告
============================
变更：#{change_id} — {subject}
项目：{project}  分支：{branch}
审查时间：{received_at}
审查结果：【PASS】 或 【FAIL】
============================

## 提交信息审查
{问题列表，无问题则写"✅ 符合规范"}

## 文件审查

### {file_path} ({status: M=修改/A=新增/D=删除})
{问题列表或"✅ 无问题"}

（每个问题格式：）
[{级别}] 行 {line}: {问题描述}
→ 原因：{违反的规范条目}
→ 建议：{具体修改建议}

============================
汇总：
- 🔴 CRITICAL: {n} 项
- 🟠 ERROR: {n} 项
- 🟡 WARNING: {n} 项
- 🔵 INFO: {n} 项
============================
```

**判断 PASS/FAIL：**
- 有任意 🔴 CRITICAL 或 🟠 ERROR → **FAIL**
- 仅有 WARNING / INFO → **PASS**

---

### 阶段五 — 提交 Review 结果

#### 5A — 测试模式（`test_mode: true`，默认）

将报告输出到当前会话（不写 Gerrit）：

```
[测试模式] 以下为 Code Review 报告，未提交到 Gerrit：
{报告内容}
```

#### 5B — 正式模式（`test_mode: false`）

```bash
# 将报告保存到临时文件
cat > /tmp/review_report.txt << 'REPORT'
{报告内容}
REPORT

# 提交到 Gerrit
python3 "$SKILL_DIR/scripts/post_review.py" \
  --workspace "$SKILL_WORKSPACE" \
  --change-id {change_id} \
  --revision {revision} \
  --report-file /tmp/review_report.txt \
  --result {PASS|FAIL}
```

退出码说明：`0` = 成功，`1` = Gerrit 写入失败，`2` = test_mode 激活（未发送）

---

## 配置参考

### 配置文件搜索路径（优先级从高到低）

| 优先级 | 路径 | 说明 |
|---|---|---|
| 1 ✅ 推荐 | `{workspace}/config/agent-code-review/agent_code_review_config.json` | 在此创建 |
| 2 | `{workspace}/config/agent_code_review_config.json` | |
| 3 | `{workspace}/agent_code_review_config.json` | |
| 4 | `{skill-dir}/agent_code_review_config.json` | 开发/测试回退 |
| 5 | `$HOME/.config/agent-code-review/agent_code_review_config.json` | 用户级 |
| 6 | `$HOME/.config/agent_code_review_config.json` | |
| 7 | `$HOME/agent_code_review_config.json` | |

`{workspace}` = `SKILL_WORKSPACE` 环境变量，`{skill-dir}` = `SKILL_DIR` 环境变量。

### ensure_stream_listener.py 中 gerrit-api 安装目录检测顺序

| 优先级 | 路径 |
|---|---|
| 1 | `GERRIT_API_SKILL_DIR` 环境变量 |
| 2 | `{workspace}/.agents/skills/gerrit-api` |
| 3 | `$HOME/.agents/skills/gerrit-api` |

若自动检测失败，可手动设置：`export GERRIT_API_SKILL_DIR=/path/to/gerrit-api`

---

## 脚本 CLI 参考

### ensure_stream_listener.py

```
python3 scripts/ensure_stream_listener.py [options]

--workspace DIR        项目 workspace（覆盖 SKILL_WORKSPACE / cwd）
--pid-file PATH        监听进程 PID 文件路径（默认 {workspace}/gerrit_stream_listener.pid）
--events-file PATH     事件队列文件（默认配置文件中的 events_file 或 {workspace}/events.jsonl）
--config FILE          agent_code_review_config.json 路径
--gerrit-api-dir DIR   gerrit-api skill 目录（覆盖自动检测）
--dry-run              仅检查，不启动进程
--verbose              DEBUG 日志

退出码：0=正常运行或启动成功，1=启动失败，2=gerrit-api 未安装
```

### poll_events.py

```
python3 scripts/poll_events.py [options]

--config FILE          agent_code_review_config.json 路径
--workspace DIR        项目 workspace
--events-file PATH     事件队列文件（覆盖配置）
--gerrit-config FILE   gerrit_config.json 路径
--max-events N         最多处理 N 条（0 = 全部）
--dry-run              只读不清空队列，不拉 diff
--verbose              DEBUG 日志

输出：JSON 到 stdout，含 test_mode 和 events 数组
```

### post_review.py

```
python3 scripts/post_review.py [options]

--change-id ID         Gerrit 变更编号（必填）
--revision REV         Revision SHA 或 "current"（默认 current）
--report-file PATH     报告文件路径，"-" 表示读 stdin
--result PASS|FAIL     审查结果（必填）
--config FILE          配置文件路径
--gerrit-config FILE   gerrit_config.json 路径
--workspace DIR        项目 workspace
--force                忽略 test_mode，强制发送到 Gerrit
--dry-run              打印 payload，不发送
--verbose              DEBUG 日志

退出码：0=成功，1=错误，2=test_mode 激活（未发送）
```

---

## 故障排查

| 症状 | 检查项 | 解决方案 |
|---|---|---|
| `ensure_stream_listener.py` 退出码 2 | gerrit-api skill 未安装 | 按 Step 1 安装 gerrit-api |
| 队列文件持续为空 | 监听进程有没有在运行？事件流有数据吗？ | 手动检查：`python3 "$GERRIT_API_SKILL_DIR/scripts/gerrit_stream_events.py" --dry-run --summary --max-events 3` |
| `poll_events.py` 输出 `error` 字段 | Gerrit 凭据是否配置？ | 按 gerrit-api/SKILL.md 配置 Gerrit 凭据 |
| `post_review.py` 退出码 2 | `test_mode: true` | 将 `test_mode` 改为 `false`，或加 `--force` |
| `post_review.py` HTTP 403 | Gerrit 账号无 Verified 投票权限 | 请 Gerrit 管理员授权 |
| `post_review.py` HTTP 401 | Gerrit 密码错误 | 重新生成 HTTP Credentials |
| 路径错误 | `SKILL_DIR` 或 `SKILL_WORKSPACE` 未正确设置 | 重新执行 Step 0A + 0B |

---

## 安全注意事项

- `agent_code_review_config.json` 必须加入 `.gitignore`
- 脚本日志中**不会打印** Gerrit 密码或 hook token
- 默认 `test_mode: true`，充分验证后再切换为 `false`
- 正式模式下 agent 有写 Gerrit（comment + Verified 标签）的权限，请确认授权范围

---

## 文件清单

```
agent-code-review/
├── SKILL.md                                    ← 本文件
├── README.md                                   ← 快速说明
└── scripts/
    ├── ensure_stream_listener.py               ← 健康检查 + 自动重启
    ├── poll_events.py                          ← 队列读取 + diff 拉取
    ├── post_review.py                          ← Gerrit comment + Verified 标签
    └── agent_code_review_config.json.example  ← 配置模板
```
