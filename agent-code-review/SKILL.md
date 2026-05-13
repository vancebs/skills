---
name: agent-code-review
description: >
  Automated Gerrit code review skill. A cron job runs review_job.py every minute:
  it manages the stream-events listener, reads new patchsets, and fetches diffs.
  The LLM then reviews each diff against T2MCodingRule and posts results via
  post_result.py (comment + Verified label). Default test_mode only prints
  results; set test_mode=false to write to Gerrit.
dependencies:
  - T2MCodingRule
compatibility: Requires python3 (≥3.9) and ssh. Python stdlib only — no pip needed.
---

# Agent Code Review Skill

**功能：** 自动化 Code Review。Cron job 每分钟运行一次，检测 Gerrit 新提交，由 LLM 按 T2Mobile 编码规范审查，生成中文报告，并（正式模式下）写回 Gerrit。

**脚本（Python stdlib，无需 pip）：**

| 脚本 | 用途 | 调用时机 |
|---|---|---|
| `check_env.py` | 环境 & 依赖检查，输出通过/失败 | 加载 skill 后运行一次 |
| `review_job.py` | 主任务：管理监听进程 + 读取事件 + 拉取 diff | Cron job 每次触发 |
| `post_result.py` | 提交 review 结果到 Gerrit | LLM 完成审查后调用 |

---

## ⚠️ Step 0 — 初始化环境变量（每次会话执行一次）

> 如果遇到路径相关问题，安装 `skill-guide`：`npx skills add https://github.com/vancebs/skills --skill skill-guide`

```bash
# Linux / macOS / Git Bash
export SKILL_WORKSPACE="$(pwd)"
export SKILL_DIR=$(python3 -c "
import os, sys
from pathlib import Path
name = 'agent-code-review'
ws = Path(os.environ.get('SKILL_WORKSPACE', os.getcwd()))
for p in [ws/'.agents'/'skills'/name, Path.home()/'.agents'/'skills'/name]:
    if p.is_dir():
        print(p); sys.exit(0)
sys.exit(1)
") || echo "ERROR: skill not found — npx skills add https://github.com/vancebs/skills --skill agent-code-review"

# Windows PowerShell
$env:SKILL_WORKSPACE = (Get-Location).Path
$skillName = 'agent-code-review'
$env:SKILL_DIR = @(
    "$env:SKILL_WORKSPACE\.agents\skills\$skillName",
    "$HOME\.agents\skills\$skillName"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
```

---

## Step 1 — 环境检查（首次加载 skill 时运行一次）

```bash
python3 "$SKILL_DIR/scripts/check_env.py"
```

脚本会逐项检查：Python 版本、SSH 命令、配置文件、Gerrit REST 连接、SSH 连接、Workspace 写权限。
**按输出提示逐一解决问题，所有项显示 ✅ 后继续。**

---

## Step 2 — 创建配置文件（一次性）

```bash
# Linux / macOS
mkdir -p "$SKILL_WORKSPACE/config/agent-code-review"
cp "$SKILL_DIR/scripts/config.json.example" \
   "$SKILL_WORKSPACE/config/agent-code-review/code_review_config.json"
# 然后编辑填写真实值
```

```batch
:: Windows CMD
mkdir "%SKILL_WORKSPACE%\config\agent-code-review"
copy "%SKILL_DIR%\scripts\config.json.example" ^
     "%SKILL_WORKSPACE%\config\agent-code-review\code_review_config.json"
```

**配置文件内容说明：**

```json
{
  "url":          "https://gerrit.example.com",
  "username":     "john.doe",
  "password":     "http-credentials-token",
  "ssh_host":     "",
  "ssh_port":     29418,
  "ssh_username": "",
  "ssh_key":      "",
  "test_mode":          true,
  "events_file":        "",
  "review_projects":    [],
  "review_branches":    [],
  "skip_file_patterns": []
}
```

| 字段 | 默认值 | 说明 |
|---|---|---|
| `url` | — | Gerrit 地址（必填） |
| `username` | — | Gerrit 用户名（必填） |
| `password` | — | HTTP Credentials token（必填）<br>生成：Gerrit → Settings → HTTP Credentials → Generate Password |
| `ssh_host` | 从 `url` 提取 | SSH 主机名（通常不需填） |
| `ssh_port` | `29418` | SSH 端口 |
| `ssh_username` | 同 `username` | SSH 用户名（通常不需填） |
| `ssh_key` | 自动检测 `~/.ssh/` | SSH 私钥路径 |
| `test_mode` | `true` | **true** = 仅输出报告，不写 Gerrit；**false** = 发布到 Gerrit |
| `events_file` | `{workspace}/events.jsonl` | 事件队列文件（留空用默认） |
| `review_projects` | `[]`（全部） | 只审查指定项目（空 = 全部） |
| `review_branches` | `[]`（全部） | 只审查指定分支（空 = 全部） |
| `skip_file_patterns` | `[]` | 跳过匹配此 glob 的文件，如 `["*.md","*.xml"]` |

> ⚠️ 将配置文件加入 `.gitignore`：`config/agent-code-review/code_review_config.json`
>
> ⚠️ SSH 公钥必须上传到 Gerrit：Settings → SSH Keys → Add Key

重新运行 `check_env.py` 确认所有项 ✅ 后继续。

---

## Step 3 — 配置 Cron Job

Cron job 每 1 分钟触发一次，执行"工作流"（见下方）。

### OpenClaw 配置

在 OpenClaw 中创建 cron job，间隔设为 **1 分钟**，将以下参考 prompt 粘贴为 cron job 内容：

```
执行 agent-code-review 工作流：

1. 运行以下命令并读取输出：
   python3 "$SKILL_DIR/scripts/review_job.py" --workspace "$SKILL_WORKSPACE"

2. 解析 JSON 输出：
   - 如果 status == "error"：输出错误信息，停止本次执行
   - 如果 events_count == 0：输出"暂无新提交"，停止本次执行
   - 如果 events_count > 0：对每个 event 执行 Code Review（见下方工作流）

3. 对每个 event，完成 Code Review 后运行：
   python3 "$SKILL_DIR/scripts/post_result.py" \
     --workspace "$SKILL_WORKSPACE" \
     --change-id {event.change_id} \
     --revision {event.revision} \
     --result {PASS 或 FAIL} \
     --report "{review 报告文本}"

注意：
- SKILL_WORKSPACE 和 SKILL_DIR 必须在会话开始时设置（Step 0）
- 加载 T2MCodingRule skill 以获取编码规范
```

### 通用平台配置

如果你的平台不支持 cron job，可以手动触发，或用后台轮询脚本：

**手动触发：** 每次 Gerrit 有新提交时，运行以下命令并按"工作流"处理输出：

```bash
python3 "$SKILL_DIR/scripts/review_job.py" --workspace "$SKILL_WORKSPACE"
```

**后台轮询（Python）：** 将以下脚本保存为 `poller.py` 并在后台运行：

```python
# poller.py — 每分钟检查一次，输出供 agent 处理
import time, subprocess, sys, os
skill_dir = os.environ.get("SKILL_DIR", "")
workspace = os.environ.get("SKILL_WORKSPACE", os.getcwd())
while True:
    result = subprocess.run(
        [sys.executable, f"{skill_dir}/scripts/review_job.py",
         "--workspace", workspace],
        capture_output=True, text=True
    )
    if result.stdout.strip():
        print(result.stdout)
    time.sleep(60)
```

---

## 📋 工作流（每次 Cron 触发时执行）

### 阶段一 — 运行主任务脚本

```bash
python3 "$SKILL_DIR/scripts/review_job.py" --workspace "$SKILL_WORKSPACE"
```

**脚本内部自动完成：**
1. 检查 SSH 监听进程是否在运行（读取 `{workspace}/gerrit_listener.pid`）
2. 如已停止 → 自动重启（`ssh ... gerrit stream-events` 后台进程）
3. 读取 `events.jsonl` 中的新事件（游标推进，不重复处理）
4. 对每个 patchset-created 事件：拉取 commit message 和所有文件 diff
5. 输出 JSON 到 stdout

**输出 JSON 结构：**

```json
{
  "status":          "ok",
  "test_mode":       true,
  "listener_status": "running",
  "events_count":    1,
  "events": [
    {
      "change_id":       "12345",
      "patchset_number": 1,
      "project":         "myOrg/myRepo",
      "branch":          "main",
      "subject":         "Fix login bug",
      "uploader":        "john.doe",
      "revision":        "abc123def456...",
      "received_at":     "2026-05-13T05:55:00Z",
      "commit_message":  "Fix login bug\n\nChange-Id: I...",
      "files": [
        {
          "path":   "src/main/java/com/example/LoginService.java",
          "status": "MODIFIED",
          "diff":   "- old line\n+ new line\n..."
        }
      ]
    }
  ]
}
```

**判断下一步：**
- `status == "error"` → 输出错误信息，停止本次执行
- `events_count == 0` → 输出"暂无新提交"，停止本次执行
- `events_count > 0` → 进入 Code Review（下方）

---

### 阶段二 — Code Review（对每个 event）

加载 **T2MCodingRule** skill，按以下步骤逐项审查：

#### 2A — 提交信息（Commit Message）检查

- [ ] 格式：`type(scope): subject`（type 为 feat/fix/refactor/docs/test/chore/style/perf 之一）
- [ ] subject 不超过 50 字符，不以句号结尾
- [ ] Body 包含 Jira ID（如 `Issue: PROJ-123`）
- [ ] Breaking Change 有 `BREAKING CHANGE:` 行

#### 2B — 每个文件 Diff 审查

根据文件扩展名选择对应规范：

| 扩展名 | 规范 |
|---|---|
| `.java` | T2MCodingRule 四（Java 编码规范） |
| `.c`, `.h` | T2MCodingRule 五（C 编码规范） |
| `.cpp`, `.cc`, `.hpp` | T2MCodingRule 六（C++ 编码规范） |
| 其他 | 通用质量检查 |

审查重点：
- [ ] 命名规范（类/变量/函数）
- [ ] 注释完整性（公共 API、复杂逻辑）
- [ ] 安全规范（T2MCodingRule 七）：无硬编码密码、日志无敏感信息
- [ ] 兼容性规范（T2MCodingRule 八）：无废弃 API、接口向后兼容
- [ ] 明显逻辑错误、资源泄漏、死锁风险

#### 2C — 问题定级

| 级别 | 说明 | 对结果影响 |
|---|---|---|
| 🔴 CRITICAL | 编译错误、安全漏洞、严重数据风险 | 导致 FAIL |
| 🟠 ERROR | 违反 T2MCodingRule 强制规则 | 导致 FAIL |
| 🟡 WARNING | 建议改进、非 T2M 覆盖语言问题 | 不影响结果 |
| 🔵 INFO | 风格建议 | 不影响结果 |

**判断 PASS / FAIL：** 有任意 🔴 CRITICAL 或 🟠 ERROR → **FAIL**，否则 **PASS**。

#### 2D — 生成报告

```
============================
Code Review 报告
============================
变更：#{change_id} — {subject}
项目：{project}  分支：{branch}
审查结果：【PASS】 或 【FAIL】
============================

## 提交信息审查
{问题列表，或"✅ 符合规范"}

## 文件审查

### {file_path} ({status})
[{级别}] 行 {line}: {问题描述}
→ 原因：{违反的规范条目}
→ 建议：{具体修改建议}

============================
汇总：🔴 {n}  🟠 {n}  🟡 {n}  🔵 {n}
============================
```

---

### 阶段三 — 提交结果

```bash
python3 "$SKILL_DIR/scripts/post_result.py" \
  --workspace "$SKILL_WORKSPACE" \
  --change-id {change_id} \
  --revision  {revision} \
  --result    {PASS 或 FAIL} \
  --report    "{报告文本}"
```

**或通过文件传入报告（报告较长时推荐）：**

```bash
# 将报告写入临时文件
cat > /tmp/review_report.txt << 'REPORT'
{报告内容}
REPORT

python3 "$SKILL_DIR/scripts/post_result.py" \
  --workspace "$SKILL_WORKSPACE" \
  --change-id {change_id} \
  --result    {PASS 或 FAIL} \
  --report-file /tmp/review_report.txt
```

**退出码说明：**

| 退出码 | 含义 |
|---|---|
| `0` | 成功（已提交到 Gerrit，或 test_mode 下已展示） |
| `1` | 提交失败（查看错误信息） |
| `2` | test_mode 激活，未提交到 Gerrit |

---

## 配置参考

### 配置文件搜索路径（优先级从高到低）

| 优先级 | 路径 |
|---|---|
| 1 ✅ 推荐 | `{workspace}/config/agent-code-review/code_review_config.json` |
| 2 | `{workspace}/config/code_review_config.json` |
| 3 | `{workspace}/code_review_config.json` |
| 4 | `{skill-dir}/code_review_config.json` |
| 5 | `$HOME/.config/agent-code-review/code_review_config.json` |
| 6 | `$HOME/.config/code_review_config.json` |
| 7 | `$HOME/code_review_config.json` |

### 运行时文件（自动创建）

| 文件 | 说明 |
|---|---|
| `{workspace}/events.jsonl` | Gerrit 事件队列（SSH 监听器写入） |
| `{workspace}/gerrit_listener.pid` | SSH 监听进程 PID |
| `{workspace}/events.cursor` | 事件读取游标（防止重复处理） |

---

## 故障排查

| 症状 | 检查项 | 解决方案 |
|---|---|---|
| check_env.py 有 ❌ 项 | 按输出提示逐一修复 | 修复后重新运行 check_env.py |
| listener_status: start_failed | SSH 命令不存在或配置错误 | 检查 ssh_host、ssh_port、SSH 密钥 |
| events_count 持续为 0 | 监听进程是否有事件？ | 手动测试：`ssh -p 29418 user@host gerrit stream-events` |
| post_result.py 退出码 2 | test_mode=true | 配置改为 false 或加 --force |
| post_result.py HTTP 403 | 账号无 Verified 投票权限 | 请 Gerrit 管理员授权 |
| post_result.py HTTP 401 | password 配置错误 | 重新生成 HTTP Credentials |
| 配置文件未找到 | SKILL_WORKSPACE 未设置？ | 重新执行 Step 0，重新运行 check_env.py |

---

## 安全注意

- `code_review_config.json` 必须加入 `.gitignore`
- 脚本日志不打印 `password` 字段
- 默认 `test_mode: true`，充分验证后再改为 `false`

## 文件清单

```
agent-code-review/
├── SKILL.md
├── README.md
└── scripts/
    ├── check_env.py          ← 环境检查（首次运行）
    ├── review_job.py         ← 主任务（cron 调用）
    ├── post_result.py        ← 提交结果到 Gerrit
    └── config.json.example  ← 配置模板
```
