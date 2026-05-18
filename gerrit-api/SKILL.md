---
name: gerrit-api
description: Interact with Gerrit Code Review via the REST API — query changes, fetch diffs, post reviews with labels and inline comments, and manage change lifecycle. Also supports real-time event streaming via SSH (stream-events).
license: Apache-2.0
compatibility: Requires python3 (≥3.9) and ssh. All scripts use Python stdlib only — no pip install needed.
metadata:
  based-on: https://github.com/yurnov/gerrit-in-5-min (gerrit-review skill by @yurnov)
  keywords: [gerrit, code review, code review automation, developer tools, stream-events, ssh]
---

# Gerrit API Skill

**What this skill does:** Query Gerrit changes, read diffs, post code reviews, manage change lifecycle (submit / abandon / restore), and listen to real-time SSH event streams.

**Scripts (no pip install needed):**
- `scripts/gerrit_api.py` — REST API operations (cross-platform, Python stdlib)
- `scripts/gerrit_stream_events.py` — SSH stream-events listener

---

## ⚠️ Step 0 — 初始化环境变量（每次会话执行一次）

> 如果遇到路径相关问题，安装 `skill-guide` 获取详细指引：`npx skills add https://github.com/vancebs/skills --skill skill-guide`

### Step 0A — 记录 Workspace

```bash
# Linux / macOS / Git Bash
export SKILL_WORKSPACE="$(pwd)"

# Windows CMD
set SKILL_WORKSPACE=%CD%

# Windows PowerShell
$env:SKILL_WORKSPACE = (Get-Location).Path
```

### Step 0B — 确认 Skill 安装目录（SKILL_DIR）

```bash
# Linux / macOS
export SKILL_DIR=$(python3 -c "
import os, sys; from pathlib import Path; n='gerrit-api'
ws = Path(os.environ.get('SKILL_WORKSPACE', os.getcwd()))
[print(p) or sys.exit(0) for p in [ws/'.agents'/'skills'/n, Path.home()/'.agents'/'skills'/n] if p.is_dir()]
sys.exit(1)") || echo "❌ gerrit-api not found: npx skills add https://github.com/vancebs/skills --skill gerrit-api"
```

> 如需 Windows PowerShell 版本、验证命令，或同时使用多个 skill 时发生 `SKILL_DIR` 冲突，参见：
> - **skill-guide Step 2**（SKILL_DIR 检测完整方法）
> - **skill-guide 错误 7**（多 skill SKILL_DIR 冲突处理）

---

## ✅ Setup Checklist

Complete these steps once before using the skill.

### Step 1 — Verify Prerequisites

```bash
python3 --version   # must be ≥ 3.9
ssh -V              # must be installed (for stream-events only)
```

### Step 2 — Create Config File

```bash
# Create directory at the recommended (highest-priority) location
mkdir -p "$SKILL_WORKSPACE/config/gerrit-api"

# Copy the template from the skill's installation directory
cp "$SKILL_DIR/scripts/gerrit_config.json.example" \
   "$SKILL_WORKSPACE/config/gerrit-api/gerrit_config.json"

# Edit with your real credentials
```

Config file content:
```json
{
  "url": "https://gerrit.example.com",
  "username": "john.doe",
  "password": "your-http-credential-token",
  "ssh_host": "gerrit.example.com",
  "ssh_port": 29418,
  "ssh_username": "john.doe",
  "ssh_key": "~/.ssh/id_rsa",
  "hook_url": "",
  "hook_token": "",
  "outbox_path": ""
}
```

> **IMPORTANT — HTTP Password:** This is NOT your Gerrit login password. Generate it at: **Gerrit web UI → Settings → HTTP Credentials → Generate Password**
>
> **IMPORTANT — SSH Key:** For stream-events, your SSH public key must be uploaded at: **Gerrit web UI → Settings → SSH Keys → Add Key**

Add to `.gitignore`:
```
config/gerrit-api/gerrit_config.json
```

### Step 3 — Test the Connection

```bash
python3 "$SKILL_DIR/scripts/gerrit_api.py" query "status:open+limit:1"
```

Expected: JSON output with change data. If you see an error, see **Troubleshooting** below.

### Step 4 — (Stream Events Only) Test SSH Connection

```bash
ssh -p 29418 john.doe@gerrit.example.com gerrit version
```

Expected: `gerrit version 3.x.x`

---

## ⚡ Quick Reference — REST API Commands

All commands follow the pattern: `python3 "$SKILL_DIR/scripts/gerrit_api.py" <command> [args]`

| Task | Command |
|---|---|
| Query open changes | `query "status:open+limit:10"` |
| Get change details | `get-change <change-id>` |
| List changed files | `list-files <change-id>` |
| Get file diff | `get-diff <change-id> "path/to/file.java"` |
| Get file content | `get-content <change-id> "path/to/file.java"` |
| Post review + label | `review <change-id> current '<json>'` |
| Post draft comment | `create-draft <change-id> current '<json>'` |
| Submit a change | `submit <change-id>` |
| Abandon a change | `abandon <change-id>` |
| Restore a change | `restore <change-id>` |
| Add a reviewer | `add-reviewer <change-id> <email>` |
| Set topic | `set-topic <change-id> <topic>` |

Use `current` as the revision to target the latest patch set.

---

## 📋 Task Workflows

### Workflow A — Review a Change (Step-by-Step Checklist)

Use this when you need to perform a code review on a Gerrit change.

**Checklist:**
- [ ] 1. Record workspace: `export SKILL_WORKSPACE="$(pwd)"`
- [ ] 2. Find changes needing review:
  ```bash
  python3 "$SKILL_DIR/scripts/gerrit_api.py" query "status:open+reviewer:self+-owner:self"
  ```
- [ ] 3. Get the change details for change `<id>`:
  ```bash
  python3 "$SKILL_DIR/scripts/gerrit_api.py" get-change <id>
  ```
- [ ] 4. List modified files:
  ```bash
  python3 "$SKILL_DIR/scripts/gerrit_api.py" list-files <id>
  ```
- [ ] 5. Review each file's diff:
  ```bash
  python3 "$SKILL_DIR/scripts/gerrit_api.py" get-diff <id> "path/to/file.java"
  ```
- [ ] 6. Post review (choose one option):

  **Option A — Inline comments + label in one call:**
  ```bash
  python3 "$SKILL_DIR/scripts/gerrit_api.py" review <id> current '{
    "message": "Review comment here.",
    "labels": {"Code-Review": 1},
    "comments": {
      "path/to/file.java": [
        {"line": 42, "message": "Consider a constant here.", "unresolved": true}
      ]
    }
  }'
  ```

  **Option B — Draft comments first, then publish:**
  ```bash
  # Add draft (repeat for each comment)
  python3 "$SKILL_DIR/scripts/gerrit_api.py" create-draft <id> current \
    '{"path":"path/to/file.java","line":42,"message":"Consider a constant.","unresolved":true}'
  # Publish all drafts with a label
  python3 "$SKILL_DIR/scripts/gerrit_api.py" review <id> current \
    '{"message":"See inline comments.","labels":{"Code-Review":-1},"drafts":"PUBLISH"}'
  ```

- [ ] 7. (Optional) Submit if approved:
  ```bash
  python3 "$SKILL_DIR/scripts/gerrit_api.py" submit <id>
  ```

**Label values** (project-specific, typical):
- `Code-Review`: `-2` reject, `-1` needs work, `0` neutral, `+1` looks good, `+2` approved
- `Verified`: `-1` fails, `0` neutral, `+1` verified

---

### Workflow B — Monitor Events with Stream Listener (Step-by-Step Checklist)

Use this when you need to react to Gerrit events in real time or collect events for batch processing.

**Decide your mode first:**

| Mode | When to use | Command flag |
|---|---|---|
| Write to file only | Collect events for later processing | `--output` |
| Push to HTTP hook only | Deliver to a local service | `--no-output --hook-url` |
| Both (recommended for prod) | File as safety net + hook for real-time | `--output --hook-url` |
| Dry run | Testing / debugging (no writes) | `--dry-run --summary` |

**Checklist:**
- [ ] 1. Record workspace: `export SKILL_WORKSPACE="$(pwd)"`
- [ ] 2. Test SSH: `ssh -p 29418 <username>@<host> gerrit version`
- [ ] 3. Test with dry run (no file writes, verify events arrive):
  ```bash
  python3 "$SKILL_DIR/scripts/gerrit_stream_events.py" \
    --workspace "$SKILL_WORKSPACE" --dry-run --summary --max-events 5
  ```
- [ ] 4. Start the background listener:
  ```bash
  # Write to file + auto-reconnect
  python3 "$SKILL_DIR/scripts/gerrit_stream_events.py" \
    --workspace "$SKILL_WORKSPACE" \
    --output "$SKILL_WORKSPACE/events.jsonl" \
    --reconnect --quiet &
  echo "Listener PID: $!"
  ```
- [ ] 5. Filter by event type / project / branch (add as needed):
  ```bash
  --filter patchset-created,change-merged   # only these event types
  --project myOrg/myRepo                    # only this project
  --branch main                             # only this branch
  ```
- [ ] 6. Read events (from file):
  ```bash
  # Python — reliable cross-platform reader (no jq dependency)
  python3 - <<'EOF'
  import json
  with open("events.jsonl") as f:
      for line in f:
          line = line.rstrip("\n")
          if not line:
              continue
          ev = json.loads(line)
          print(ev["type"], ev.get("change", {}).get("number", ""))
  EOF
  ```
- [ ] 7. Stop the listener when done: `kill <PID>`

---

## Configuration Reference

### Config File Search Order (Highest Priority First)

> Follows **skill-guide Rule 3** (config file search order). If config is not being loaded, see skill-guide Error 2.

| Priority | Path | Notes |
|---|---|---|
| 1 ✅ preferred | `{workspace}/config/gerrit-api/gerrit_config.json` | Create here |
| 2 | `{workspace}/config/gerrit_config.json` | |
| 3 | `{workspace}/gerrit_config.json` | |
| 4 | `{skill-dir}/gerrit_config.json` | Dev/testing fallback |
| 5 | `$HOME/.config/gerrit-api/gerrit_config.json` | Per-user |
| 6 | `$HOME/.config/gerrit_config.json` | |
| 7 | `$HOME/gerrit_config.json` | |

`{workspace}` = value of `SKILL_WORKSPACE` env var, or the directory where the script is invoked.

### Environment Variables (fallback when no config file)

| Variable | Config key | Default | Required |
|---|---|---|---|
| `GERRIT_URL` | `url` | — | ✅ Yes |
| `GERRIT_USERNAME` | `username` | — | ✅ Yes |
| `GERRIT_HTTP_PASSWORD` | `password` | — | ✅ Yes |
| `GERRIT_SSH_HOST` | `ssh_host` | derived from `url` | No |
| `GERRIT_SSH_PORT` | `ssh_port` | `29418` | No |
| `GERRIT_SSH_USERNAME` | `ssh_username` | same as `username` | No |
| `GERRIT_SSH_KEY` | `ssh_key` | `~/.ssh/` defaults | No |
| `HOOK_URL` | `hook_url` | — | No |
| `HOOK_TOKEN` | `hook_token` | — | No |
| `OUTBOX_PATH` | `outbox_path` | `{workspace}/events.outbox.jsonl` | No |

Set env vars:
```bash
export GERRIT_URL="https://gerrit.example.com"
export GERRIT_USERNAME="john.doe"
export GERRIT_HTTP_PASSWORD="your-token"
```

---

## SSH Stream Events — Full Reference

### How it works

1. Script opens SSH to Gerrit port 29418 (configurable).
2. Runs `gerrit stream-events` on the server.
3. Gerrit emits one JSON line per event.
4. Script enriches each event with `_received_at` (ISO timestamp) and `summary` (human-readable description).
5. Events go to stdout, optionally to a JSONL file and/or HTTP hook.

### Script Options Reference

```
python3 scripts/gerrit_stream_events.py [options]

Config:
  --config FILE         Config file (searches 7 locations if omitted)
  --workspace DIR       Project workspace dir (overrides SKILL_WORKSPACE / cwd)

Filtering:
  --filter TYPES        Comma-separated event types to include (default: all)
  --project NAMES       Comma-separated project names to filter
  --branch NAMES        Comma-separated branch names to filter

File output:
  --output PATH         Append events to PATH as compact JSONL
  --no-output           Disable file output even if --output is set
  --atomic-write        Atomic O_APPEND+fsync writes (default: on)
  --no-atomic-write     Disable atomic file writes (compatibility mode)

HTTP hook:
  --hook-url URL        POST each event as JSON to this URL
  --hook-token TOKEN    X-Auth-Token header value (never logged)
  --hook-retries N      Max hook retries on 5xx/network error (default: 3)
  --hook-timeout SECS   HTTP request timeout in seconds (default: 3)
  --outbox PATH         Append undelivered events here
                        (default: {workspace}/events.outbox.jsonl)

Daemon / process:
  --pid-file PATH       Write PID to PATH on startup; remove on clean exit
  --dry-run             Parse and print events; skip all writes and hooks

Stream control:
  --max-events N        Stop after N events (0 = unlimited)
  --timeout SECS        Stop after SECS seconds (0 = unlimited)
  --reconnect           Reconnect on connection loss (exponential back-off)
  --reconnect-delay N   Initial reconnect delay in seconds (default: 5)

Display:
  --pretty              Pretty-print JSON output to stdout
  --summary             Emit one-line human-readable summaries instead of JSON
  --verbose             Enable DEBUG-level logging
  --quiet               Suppress all log output
```

### HTTP Hook

When `--hook-url` is set, each accepted event is POSTed as JSON to that URL.

**Request format:**
```
POST /your-path HTTP/1.1
Content-Type: application/json
X-Auth-Token: <token>   ← only when --hook-token is set

{ "type": "patchset-created", "change": {...}, "_received_at": "...", "summary": "..." }
```

**Response handling:**

| HTTP status | Behaviour |
|---|---|
| 2xx | Delivered ✅ |
| 4xx | Client error — not retried |
| 5xx / timeout | Retry up to `--hook-retries` times (exp. backoff 0.5 s × 2ⁿ ± 10 % jitter), then write to outbox |

> ⚠️ **Security:** Only point `--hook-url` at `127.0.0.1` or a UNIX socket. For external hosts, use TLS.

### Foreground / systemd

The script does not daemonize itself. Example systemd unit:

```ini
[Unit]
Description=Gerrit stream-events listener
After=network.target

[Service]
# SKILL_WORKSPACE = agent's project dir (for config file & events.jsonl)
# SKILL_DIR       = gerrit-api skill installation directory
Environment=SKILL_WORKSPACE=/opt/gerrit-workspace
Environment=SKILL_DIR=/home/user/.agents/skills/gerrit-api
ExecStart=/usr/bin/python3 ${SKILL_DIR}/scripts/gerrit_stream_events.py \
    --workspace ${SKILL_WORKSPACE} \
    --output ${SKILL_WORKSPACE}/events.jsonl \
    --hook-url http://127.0.0.1:8443/events \
    --hook-token *** \
    --reconnect
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Event Type Reference

| Event type | Trigger | Key extra fields |
|---|---|---|
| `patchset-created` | New patch set uploaded | `uploader`, `patchSet.number`, `patchSet.revision` |
| `change-merged` | Change submitted/merged | `submitter`, `newRev` |
| `change-abandoned` | Change abandoned | `abandoner`, `reason` |
| `change-restored` | Change restored | `restorer`, `reason` |
| `comment-added` | Review comment posted | `author`, `approvals[]`, `comment` |
| `reviewer-added` | Reviewer added | `reviewer` |
| `reviewer-deleted` | Reviewer removed | `reviewer` |
| `vote-deleted` | Vote deleted | `reviewer`, `remover`, `approvals[]` |
| `topic-changed` | Topic updated | `changer`, `oldTopic` |
| `hashtags-changed` | Hashtags updated | `editor`, `added[]`, `removed[]` |
| `ref-updated` | Git ref pushed/deleted | `submitter`, `refUpdate.project`, `refUpdate.refName`, `refUpdate.newRev` |
| `project-created` | New project created | `projectName`, `headName` |
| `pending-check-updated` | Pending check updated | `pendingChecksInfo` |

### Parsed Event Structure

Every event has these extra fields added by the script:

| Field | Description |
|---|---|
| `_received_at` | ISO 8601 UTC timestamp when the event was received |
| `summary` | Human-readable one-line description |

---

## Troubleshooting Checklist

| Symptom | Check | Fix |
|---|---|---|
| `HTTP 401 Unauthorized` | HTTP password correct? | Re-generate at Gerrit → Settings → HTTP Credentials |
| `HTTP 404 Not Found` | Change number exists? URL has trailing slash? | Verify change number; remove trailing slash from `url` |
| `HTTP 409 Conflict` | Trying to review a change-edit? Missing approvals for submit? | Check change status in Gerrit UI |
| Config file not found | Is `SKILL_WORKSPACE` set? Is file at priority-1 path? | Run `python3 "$SKILL_DIR/scripts/gerrit_api.py" help` to see search paths |
| SSH auth fails | SSH key uploaded to Gerrit? Right user/port? | Run `ssh -p 29418 <user>@<host> gerrit version` to test |
| SSH "access denied" | Account lacks Stream Events capability | Ask Gerrit admin to grant under Global Capabilities |

---

## Gerrit Concepts

### Changes and Patch Sets
- A **change** = one reviewable unit (one commit).
- Each update creates a new **patch set** (amended commit with same `Change-Id`).
- Changes live under `refs/changes/` in the git repo.

### Labels
- **Code-Review**: −2 to +2. `+2` = approved.
- **Verified**: −1 to +1. Usually set by CI.
- Ranges and names are project-specific.

### URL Encoding
Project names and file paths in REST URLs must be URL-encoded:
```
myOrg/myProject  →  myOrg%2FmyProject
src/main/App.java  →  src%2Fmain%2FApp.java
```
The `gerrit_api.py` script handles encoding automatically.

---

## REST API Reference (Direct HTTP — Advanced)

Use `gerrit_api.py` for most tasks. Only use direct HTTP if you need operations not covered by the script.

### Authentication
All authenticated endpoints use the `/a/` prefix + HTTP Basic Auth:
```bash
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/changes/?q=status:open+limit:5" | python3 -c "import sys; print(sys.stdin.read()[5:])"
```

### XSSI Prefix
All Gerrit REST responses start with `)]}'` (4 chars + newline). Strip it before parsing:
```python
body = response_text[5:]  # strip ")]}'\n"
data = json.loads(body)
```

### Key Endpoints Quick Reference

| Operation | Method | Endpoint |
|---|---|---|
| Query changes | GET | `/a/changes/?q=<query>&n=<limit>&o=<option>` |
| Get change | GET | `/a/changes/<id>?o=CURRENT_REVISION&o=DETAILED_LABELS` |
| List files | GET | `/a/changes/<id>/revisions/current/files/` |
| Get diff | GET | `/a/changes/<id>/revisions/current/files/<file>/diff` |
| Get content | GET | `/a/changes/<id>/revisions/current/files/<file>/content` |
| Post review | POST | `/a/changes/<id>/revisions/current/review` |
| Post draft | PUT | `/a/changes/<id>/revisions/current/drafts` |
| Submit | POST | `/a/changes/<id>/submit` |
| Abandon | POST | `/a/changes/<id>/abandon` |
| Restore | POST | `/a/changes/<id>/restore` |
| Add reviewer | POST | `/a/changes/<id>/reviewers` |
| Set topic | PUT | `/a/changes/<id>/topic` |

Common query options (`o=` parameter): `CURRENT_REVISION`, `DETAILED_LABELS`, `DETAILED_ACCOUNTS`, `CURRENT_FILES`, `MESSAGES`

Common query operators: `status:open`, `status:merged`, `owner:self`, `reviewer:self`, `project:<name>`, `branch:<name>`, `after:"2025-01-01"`

---

## ⛔ 约束与禁止事项

### 不支持的场景

| 场景 | 原因 | 处理动作 |
|---|---|---|
| HTTP 5xx 持续失败（超过重试上限） | 服务端不可用 | 最多重试 3 次（指数退避），超限后输出错误并终止，不得无限重试 |
| HTTP 429 Rate Limited | 请求频率超限 | 等待响应头 `Retry-After` 秒数后重试一次；若仍失败则终止 |
| 响应体无法解析（非 XSSI 格式或非 JSON） | Gerrit 版本不兼容或代理层返回 HTML | 输出原始响应前 200 字符，提示用户检查 `url` 配置和 Gerrit 版本 |
| `query` 返回多条结果（Change-Id 或 commit SHA 匹配多个变更） | 不同项目的同名 Change-Id | 只取第一条结果，日志输出 WARNING "多条结果，使用第一条" |
| `get-change` 对已删除/已废弃变更操作（`status: ABANDONED`） | 变更已关闭 | 获取后检查 `status` 字段；若为 `ABANDONED` 或 `MERGED` 时 `review` 操作不发 Verified 标签，仅发 comment |
| `events.jsonl` 最后一行无换行符（写入中断） | 写端 crash | 读端跳过不以 `\n` 结尾的最后一行，等待下次写完整行 |
| 并发多个 `gerrit_stream_events.py` 实例写同一文件 | 文件锁冲突 | 不支持，同一 `events.jsonl` 文件只允许一个写入进程 |

### 明确禁止的操作

- ⛔ **禁止将 `--hook-url` 指向非 loopback 地址（127.0.0.x）而不使用 TLS**：明文传输 token 会导致凭据泄露
- ⛔ **禁止在日志/stderr 中打印 `password`、`hook_token` 或任何凭据字段**：不论任何异常情况
- ⛔ **禁止在配置文件中硬编码密码后提交到 Git**：必须将 `config/gerrit-api/gerrit_config.json` 加入 `.gitignore`
- ⛔ **禁止对同一 change 的同一 patchset 重复提交 `review`**：非幂等操作，会产生重复评论；调用前检查该 patchset 是否已有本账号评论

### 边界条件

| 参数 | 范围 | 超限行为 |
|---|---|---|
| `--max-events` | 1–100000；默认不限 | 超过 100000 → 截断为 100000，记录 WARNING |
| `--hook-retries` | 0–10；默认 3 | 超过 10 → 启动时拒绝，exit 1 |
| `--hook-timeout` | 1–60 秒；默认 3 | 超过 60 → 截断为 60 |
| 单条事件 JSON 大小 | 无硬限制；建议 < 1 MB | 超过 1 MB 时记录 WARNING |
| 文件路径长度 | ≤ 4096 字符 | 超限 → 跳过该文件，记录 WARNING |

### 幂等性声明

| 操作 | 幂等性 | 说明 |
|---|---|---|
| `get-change`, `list-files`, `get-diff`, `query` | ✅ 幂等 | 只读，无副作用 |
| `gerrit_stream_events.py`（写文件） | ⚠️ 非幂等（有保护） | 光标文件防止重复读取 |
| `review`（post review） | ❌ 非幂等 | 重复调用会发重复评论；调用方负责去重 |
| `submit`, `abandon`, `restore` | ⚠️ 非幂等（有保护） | Gerrit 服务端拒绝对已完成状态重复操作（HTTP 409） |

---

## Security

- **Never print or log** `GERRIT_HTTP_PASSWORD`, `password` config field, or `hook_token`.
- Use environment variables or the config file to pass credentials — never hardcode them.
- Add `config/gerrit-api/gerrit_config.json` to `.gitignore`.

## Files

- `scripts/gerrit_api.py` — REST API helper (cross-platform, Python stdlib only)
- `scripts/gerrit_stream_events.py` — SSH stream-events listener with file/hook delivery
- `scripts/gerrit_config.json.example` — config template

## References

- [Gerrit REST API](https://gerrit-review.googlesource.com/Documentation/rest-api.html)
- [Gerrit Changes REST API](https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html)
- [Gerrit Search Operators](https://gerrit-review.googlesource.com/Documentation/user-search.html)
- [Gerrit Stream Events (SSH)](https://gerrit-review.googlesource.com/Documentation/cmd-stream-events.html)
