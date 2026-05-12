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

**脚本（stdlib only，无需 pip）：**
- `scripts/poll_events.py` — 原子读取事件队列，拉取 patch diff，输出给 Agent 审查
- `scripts/post_review.py` — 向 Gerrit 提交 review comment，可设置 Verified 标签

---

## ⚠️ Step 0 — 记录 Workspace（每次会话第一步）

> **问题：** 如果在会话中 `cd` 切换目录，脚本将无法找到配置文件。
>
> **解决方案：** 在执行任何命令前，先捕获 workspace 的绝对路径。

```bash
# Linux / macOS / Git Bash
export SKILL_WORKSPACE="$(pwd)"

# Windows CMD
set SKILL_WORKSPACE=%CD%

# Windows PowerShell
$env:SKILL_WORKSPACE = (Get-Location).Path
```

之后所有脚本调用都使用绝对路径：
```bash
python3 "$SKILL_WORKSPACE/scripts/poll_events.py" --workspace "$SKILL_WORKSPACE"
```

---

## ✅ 初始化配置清单（一次性，首次使用前完成）

### Step 1 — 确认依赖 Skill 已安装并配置

```bash
# 检查 gerrit-api 是否可用（应输出 JSON 变更列表）
python3 "$SKILL_WORKSPACE/scripts/gerrit_api.py" query "status:open+limit:1"

# T2MCodingRule 无需额外配置，加载 skill 即可
```

若 gerrit-api 未配置，请先按 gerrit-api/SKILL.md 完成配置。

### Step 2 — 创建 agent-code-review 配置文件

```bash
# Linux / macOS
mkdir -p "$SKILL_WORKSPACE/config/agent-code-review"
cp "$SKILL_WORKSPACE/scripts/agent_code_review_config.json.example" \
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

> **⚠️ 安全提醒：** 将配置文件加入 `.gitignore`：
> ```
> config/agent-code-review/agent_code_review_config.json
> ```

### Step 3 — 测试 Gerrit 连接与事件流

```bash
# 用 dry-run 模式验证可以拉到事件（监听 5 条后自动退出）
python3 "$SKILL_WORKSPACE/scripts/gerrit_stream_events.py" \
  --workspace "$SKILL_WORKSPACE" \
  --filter patchset-created \
  --dry-run --summary --max-events 5
```

### Step 4 — 启动事件流监听（后台长期运行）

```bash
# 启动监听，将 patchset-created 事件持续写入队列文件
python3 "$SKILL_WORKSPACE/scripts/gerrit_stream_events.py" \
  --workspace "$SKILL_WORKSPACE" \
  --output "$SKILL_WORKSPACE/events.jsonl" \
  --filter patchset-created \
  --reconnect --quiet &

echo "Stream listener PID: $!"
```

> **systemd 部署方式** 见本文末尾的附录。

### Step 5 — 配置 Cron Job（定时触发 Code Review）

**首选：使用 OpenClaw 原生 Cron Job**

在 OpenClaw 中创建 cron job，间隔 1 分钟，触发内容：
```
执行 agent-code-review 工作流（见下方"工作流"章节）
```

**备选：Python 后台轮询脚本**（平台不支持 cron 时使用）

```bash
# 启动后台轮询进程（每 60 秒执行一次）
python3 - <<'EOF' &
import time, subprocess, os, sys
workspace = os.environ.get("SKILL_WORKSPACE", os.getcwd())
script = f"{workspace}/scripts/poll_events.py"
while True:
    time.sleep(60)
    subprocess.run([sys.executable, script, "--workspace", workspace])
EOF
echo "Poller PID: $!"
```

---

## 📋 工作流：Code Review（每次 Cron 触发时执行）

> 这是 Agent 每次被 cron 触发后应执行的完整流程。

### 阶段一 — 读取事件队列

```bash
# 运行 poll_events.py，读取并清空队列，拉取 diff
python3 "$SKILL_WORKSPACE/scripts/poll_events.py" \
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

- **如果 `events` 为空数组** → 本次无新提交，结束。
- **如果 `error` 字段存在** → 检查 Gerrit 配置，见故障排查章节。

---

### 阶段二 — 逐事件 Code Review

对 `events` 数组中的每一个事件，执行以下检查：

#### 2A — 提交信息（Commit Message）检查清单

- [ ] 格式符合 T2MCodingRule 一：`type(scope): subject`
- [ ] `type` 为规范值之一（feat/fix/refactor/docs/test/chore/style/perf）
- [ ] `subject` 不超过 50 字符，不以句号结尾
- [ ] Body 中包含 Jira ID（如 `Issue: PROJ-123`）
- [ ] 如有 Breaking Change，有 `BREAKING CHANGE:` 行

#### 2B — 每个文件的 Diff 审查

对 `files` 中每一个文件：

**1. 判断语言**

| 文件扩展名 | 适用规范 |
|---|---|
| `.java` | T2MCodingRule 四（Java 编码规范） |
| `.c`, `.h` | T2MCodingRule 五（C 编码规范） |
| `.cpp`, `.cc`, `.hpp` | T2MCodingRule 六（C++ 编码规范） |
| 其他 | 通用代码质量标准（见 2C） |

**2. 按规范审查（Java/C/C++ 核心检查项）**

- [ ] **命名规范**：类/变量/函数命名是否符合规范？
- [ ] **注释规范**：公共 API / 复杂逻辑是否有必要注释？
- [ ] **安全规范**（T2MCodingRule 七）：
  - [ ] 无硬编码密码、密钥、token
  - [ ] 日志中无敏感信息明文输出
  - [ ] 权限检查是否正确（Android 相关）
- [ ] **兼容性规范**（T2MCodingRule 八）：
  - [ ] 无使用 `@Deprecated` API
  - [ ] HAL / AIDL 接口修改向后兼容
- [ ] **代码逻辑**：是否有明显错误、资源泄漏、死锁风险？

**3. 问题定级**

| 级别 | 说明 | 对结果影响 |
|---|---|---|
| 🔴 CRITICAL | 编译错误、安全漏洞、严重数据风险 | 导致 FAIL |
| 🟠 ERROR | 违反 T2MCodingRule 强制规则 | 导致 FAIL |
| 🟡 WARNING | 建议改进、通用语言非 T2M 规范问题 | 不影响结果 |
| 🔵 INFO | 风格建议、可选优化 | 不影响结果 |

#### 2C — 非 T2M 覆盖语言（通用质量审查）

仅检查以下项目（非 T2MCodingRule 规范，结果只给 WARNING / INFO）：
- 明显的命名混乱（无意义变量名如 `a`, `tmp1`）
- 重复代码块
- 过长函数（>100 行）
- 编译错误（如语法错误）
- **有以下情况则升级为 CRITICAL**：安全凭证硬编码、SQL 注入风险

---

### 阶段三 — 生成 Review 报告

按以下格式生成报告（纯文本，用于 Gerrit comment 或输出到会话）：

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
{commit message 问题列表，无问题则写"✅ 符合规范"}

## 文件审查

### {file_path} ({status: M=修改/A=新增/D=删除})
{问题列表或"✅ 无问题"}

（每个问题格式：）
[{级别}] 行 {line}: {问题描述}
→ 原因：{违反的规范条目或质量原则}
→ 建议：{具体修改建议}

============================
汇总：
- 🔴 CRITICAL: {n} 项
- 🟠 ERROR: {n} 项
- 🟡 WARNING: {n} 项
- 🔵 INFO: {n} 项
============================
```

**判断结果（PASS/FAIL）规则：**
- 存在任意 🔴 CRITICAL 或 🟠 ERROR → **FAIL**
- 仅有 WARNING / INFO → **PASS**（报告中列出建议）

---

### 阶段四 — 提交 Review 结果

#### 4A — 测试模式（默认）

将报告**输出到当前会话**（不写 Gerrit）：

```
[测试模式] 以下为 Code Review 报告，未提交到 Gerrit：
{报告内容}
```

#### 4B — 正式模式（`test_mode: false`）

```bash
# 将报告保存到临时文件
cat > /tmp/review_report.txt << 'REPORT'
{报告内容}
REPORT

# 提交到 Gerrit（自动判断 PASS/FAIL）
python3 "$SKILL_WORKSPACE/scripts/post_review.py" \
  --workspace "$SKILL_WORKSPACE" \
  --change-id {change_id} \
  --revision {revision} \
  --report-file /tmp/review_report.txt \
  --result {PASS|FAIL}
```

如果返回退出码 2，表示 test_mode 处于激活状态（报告未发送）。
如果返回退出码 1，表示 Gerrit 写入失败，检查 Gerrit 配置。

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

`{workspace}` = `SKILL_WORKSPACE` 环境变量的值，或脚本执行时的 `cwd`。

---

## 脚本 CLI 参考

### poll_events.py

```
python3 scripts/poll_events.py [options]

--config FILE          指定 agent_code_review_config.json 路径
--workspace DIR        指定 workspace（覆盖 SKILL_WORKSPACE / cwd）
--events-file PATH     事件队列文件路径（覆盖配置文件中的 events_file）
--gerrit-config FILE   指定 gerrit_config.json 路径
--max-events N         最多处理 N 条事件（0 = 全部）
--dry-run              只读不清空队列，不拉 diff（调试用）
--verbose              启用 DEBUG 日志
```

输出：JSON 到 stdout，包含 `test_mode` 和 `events` 数组（含 diff 内容）。

### post_review.py

```
python3 scripts/post_review.py [options]

--change-id ID         Gerrit 变更编号（必填）
--revision REV         Revision SHA 或 "current"（默认 current）
--report-file PATH     报告文本文件路径，"-" 表示读 stdin
--result PASS|FAIL     审查结果（必填）
--config FILE          指定 agent_code_review_config.json
--gerrit-config FILE   指定 gerrit_config.json
--workspace DIR        指定 workspace
--force                强制发送（忽略 test_mode）
--dry-run              仅打印 payload，不发送
--verbose              DEBUG 日志
```

退出码：0=成功，1=错误，2=test_mode 激活（未发送）

---

## 故障排查

| 症状 | 检查项 | 解决方案 |
|---|---|---|
| `poll_events.py` 输出 `events: []` 且无日志 | 队列文件是否存在？ | 检查 `events_file` 路径；确认 stream listener 在运行 |
| 队列文件存在但事件为空 | stream listener 是否已启动？filter 是否正确？ | 运行 `--dry-run --summary` 手工验证事件流 |
| `Gerrit credentials not configured` | gerrit-api 是否已配置？ | 按 gerrit-api/SKILL.md 配置 Gerrit 凭据 |
| `post_review.py` 退出码 2 | `test_mode: true` | 将配置中 `test_mode` 改为 `false`，或加 `--force` |
| `post_review.py` HTTP 403 | Gerrit 账号缺少 Verified 标签权限 | 请 Gerrit 管理员授予项目 `Verified` 投票权限 |
| `post_review.py` HTTP 401 | Gerrit 密码错误 | 重新生成 HTTP Credentials |
| 报告未出现在 Gerrit | `test_mode` 未关闭 | 检查配置文件中 `test_mode` 字段 |
| 路径错误（脚本找不到配置） | 未设置 `SKILL_WORKSPACE`，或会话中改变了目录 | 重新执行 Step 0（设置 SKILL_WORKSPACE） |

---

## 附录：systemd 部署（生产环境）

将 stream listener 注册为系统服务，确保重启后自动恢复：

```ini
# /etc/systemd/system/gerrit-stream-listener.service
[Unit]
Description=Gerrit stream-events listener for code review
After=network.target

[Service]
User=your-user
Environment=SKILL_WORKSPACE=/opt/code-review
ExecStart=/usr/bin/python3 /opt/code-review/scripts/gerrit_stream_events.py \
    --workspace /opt/code-review \
    --output /opt/code-review/events.jsonl \
    --filter patchset-created \
    --reconnect
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable gerrit-stream-listener
sudo systemctl start gerrit-stream-listener
```

---

## 安全注意事项

- `agent_code_review_config.json` 包含 Gerrit 凭据路径引用，必须加入 `.gitignore`
- 脚本日志中**不会打印** `password` 或 Gerrit HTTP 密码
- 建议 `test_mode: true` 在新部署中保持默认开启，充分验证后再切换为 `false`
- 正式模式下，Agent 有向 Gerrit 写数据（comment + Verified 标签）的权限，请确认授权范围

---

## 文件清单

```
agent-code-review/
├── SKILL.md                                    ← 本文件
├── README.md                                   ← 快速说明
└── scripts/
    ├── poll_events.py                          ← 队列读取 + diff 拉取
    ├── post_review.py                          ← Gerrit comment + Verified 标签
    └── agent_code_review_config.json.example  ← 配置模板
```
