---
name: gerrit-api
description: >
  This skill should be used when the user asks to "query a Gerrit change",
  "fetch a diff", "post a code review", "submit or abandon a change",
  "listen to Gerrit stream events", "get patch set files", or needs REST/SSH
  access to Gerrit. Provides Python scripts for all Gerrit REST operations
  (gerrit_api.py) and SSH stream-events listener (gerrit_stream_events.py).
  No pip install required — Python stdlib only.
license: Apache-2.0
compatibility: Requires python3 (≥3.9) and ssh. Python stdlib only — no pip install needed.
keywords:
  - gerrit
  - code review
  - REST API
  - stream-events
  - SSH
  - diff
  - patch
  - change
triggers:
  - gerrit
  - query change
  - fetch diff
  - post review
  - stream events
  - gerrit-api
metadata:
  based-on: https://github.com/yurnov/gerrit-in-5-min (gerrit-review skill by @yurnov)
---

# Gerrit API Skill

**What this skill does:** Query Gerrit changes, read diffs, post code reviews, manage change lifecycle (submit / abandon / restore), and listen to real-time SSH event streams.

**Scripts (no pip install needed):**
- `scripts/gerrit_api.py` — REST API operations (cross-platform, Python stdlib)
- `scripts/gerrit_stream_events.py` — SSH stream-events listener

---

> **路径约定**: 以下所有 `scripts/...` 路径均相对于本 Skill 目录（`.agents/skills/gerrit-api/`）。

## ✅ Setup Checklist

Complete these steps once before using the skill.

### Step 1 — Verify Prerequisites

```bash
python3 --version   # must be ≥ 3.9
ssh -V              # must be installed (for stream-events only)
```

### Step 2 — Configure Credentials

Choose **one** of the two options below. Config file takes priority over env vars.

**Option A — Config file (recommended for persistent setups)**

Create `$WORKSPACE/.config/gerrit-api.json` (or `~/.config/gerrit-api.json`):

```json
{
  "GERRIT_URL": "https://gerrit.example.com",
  "GERRIT_USERNAME": "john.doe",
  "GERRIT_HTTP_PASSWORD": "your-http-credential-token",
  "GERRIT_SSH_PORT": "29418",
  "GERRIT_SSH_KEY": "~/.ssh/id_rsa"
}
```

**Option B — Environment variables**

```bash
# Required
export GERRIT_URL="https://gerrit.example.com"
export GERRIT_USERNAME="john.doe"
export GERRIT_HTTP_PASSWORD="your-http-credential-token"

# SSH stream-events (optional — defaults derived from GERRIT_URL)
export GERRIT_SSH_HOST="gerrit.example.com"   # default: host from GERRIT_URL
export GERRIT_SSH_PORT=29418                   # default: 29418
export GERRIT_SSH_USERNAME="john.doe"          # default: GERRIT_USERNAME
export GERRIT_SSH_KEY="~/.ssh/id_rsa"          # default: ~/.ssh/id_rsa
```

Windows CMD / PowerShell:
```cmd
set GERRIT_URL=https://gerrit.example.com
set GERRIT_USERNAME=john.doe
set GERRIT_HTTP_PASSWORD=your-http-credential-token
```

> ⚠️ **HTTP Password** ≠ Gerrit login password. Generate at: Gerrit → Settings → HTTP Credentials → Generate Password  
> ⚠️ **SSH Key** must be uploaded: Gerrit → Settings → SSH Keys → Add Key

### Step 3 — Test the Connection

```bash
python3 scripts/gerrit_api.py query "status:open+limit:1"
```

Expected: JSON output with change data. On error, see **Troubleshooting** below.

### Step 4 — (Stream Events Only) Test SSH Connection

```bash
ssh -p 29418 john.doe@gerrit.example.com gerrit version
```

Expected: `gerrit version 3.x.x`

---
## ⚡ Quick Reference — Common Commands

All commands: `python3 scripts/gerrit_api.py <command> [args]`

| Task | Command |
|---|---|
| Query open changes | `query "status:open+limit:10"` |
| Get change details | `get-change <change-id>` |
| Get file diff | `get-diff <change-id> "path/to/file.java"` |
| Post review + label | `review <change-id> current '<json>'` |
| Submit a change | `submit <change-id>` |

> 📖 Full command reference and REST API endpoints: [`references/rest-api-reference.md`](references/rest-api-reference.md)

---

## 📋 Task Workflows

### Workflow A — Review a Change (Step-by-Step Checklist)

Use for performing a code review on a Gerrit change.

**Checklist:**
- [ ] 1. Find changes needing review:
  ```bash
  python3 scripts/gerrit_api.py query "status:open+reviewer:self+-owner:self"
  ```
- [ ] 3. Get the change details for change `<id>`:
  ```bash
  python3 scripts/gerrit_api.py get-change <id>
  ```
- [ ] 4. List modified files:
  ```bash
  python3 scripts/gerrit_api.py list-files <id>
  ```
- [ ] 5. Review each file's diff:
  ```bash
  python3 scripts/gerrit_api.py get-diff <id> "path/to/file.java"
  ```
- [ ] 6. Post review (choose one option):

  **Option A — Inline comments + label in one call:**
  ```bash
  python3 scripts/gerrit_api.py review <id> current '{
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
  python3 scripts/gerrit_api.py create-draft <id> current \
    '{"path":"path/to/file.java","line":42,"message":"Consider a constant.","unresolved":true}'
  # Publish all drafts with a label
  python3 scripts/gerrit_api.py review <id> current \
    '{"message":"See inline comments.","labels":{"Code-Review":-1},"drafts":"PUBLISH"}'
  ```

- [ ] 7. (Optional) Submit if approved:
  ```bash
  python3 scripts/gerrit_api.py submit <id>
  ```

**Label values** (project-specific, typical):
- `Code-Review`: `-2` reject, `-1` needs work, `0` neutral, `+1` looks good, `+2` approved
- `Verified`: `-1` fails, `0` neutral, `+1` verified

---

### Workflow B — Monitor Events with Stream Listener (Step-by-Step Checklist)

Use for reacting to Gerrit events in real time or collecting events for batch processing.

**Select the appropriate mode:**

| Mode | When to use | Command flag |
|---|---|---|
| Write to file only | Collect events for later processing | `--output` |
| Push to HTTP hook only | Deliver to a local service | `--no-output --hook-url` |
| Both (recommended for prod) | File as safety net + hook for real-time | `--output --hook-url` |
| Dry run | Testing / debugging (no writes) | `--dry-run --summary` |

**Checklist:**
- [ ] 1. Test SSH: `ssh -p 29418 <username>@<host> gerrit version`
- [ ] 3. Test with dry run (no file writes, verify events arrive):
  ```bash
  python3 scripts/gerrit_stream_events.py \
    --dry-run --summary --max-events 5
  ```
- [ ] 4. Start the background listener:
  ```bash
  # Write to file + auto-reconnect
  python3 scripts/gerrit_stream_events.py \
    --output events.jsonl \
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

> 📖 Full script options, event types, and systemd setup: [`references/stream-events-guide.md`](references/stream-events-guide.md)

---

## Configuration Reference

### Config Reference

| Env var | Required | Description |
|---|---|---|
| `GERRIT_URL` | ✅ | Gerrit base URL |
| `GERRIT_USERNAME` | ✅ | Gerrit username |
| `GERRIT_HTTP_PASSWORD` | ✅ | HTTP credential token |
| `GERRIT_SSH_HOST` | optional | SSH host (default: from GERRIT_URL) |
| `GERRIT_SSH_PORT` | optional | SSH port (default: 29418) |
| `GERRIT_SSH_USERNAME` | optional | SSH username (default: GERRIT_USERNAME) |
| `GERRIT_SSH_KEY` | optional | SSH key path (default: ~/.ssh/id_rsa) |
| `GERRIT_HOOK_URL` | optional | Webhook URL for event forwarding |
| `GERRIT_HOOK_TOKEN` | optional | Webhook token |
| `GERRIT_OUTBOX_PATH` | optional | Path to outbox file |

---


## Troubleshooting Checklist

| Symptom | Check | Fix |
|---|---|---|
| `HTTP 401 Unauthorized` | HTTP password correct? | Re-generate at Gerrit → Settings → HTTP Credentials |
| `HTTP 404 Not Found` | Change number exists? URL has trailing slash? | Verify change number; remove trailing slash from `GERRIT_URL` |
| SSH auth fails | SSH key uploaded to Gerrit? Right user/port? | Run `ssh -p 29418 <user>@<host> gerrit version` to test |
| SSH "access denied" | Account lacks Stream Events capability | Ask Gerrit admin to grant under Global Capabilities |

---


## 📚 参考文件

| 文件 | 内容 |
|---|---|
| [`references/rest-api-reference.md`](references/rest-api-reference.md) | REST API 端点速查、认证、XSSI prefix、Gerrit 概念 |
| [`references/stream-events-guide.md`](references/stream-events-guide.md) | SSH stream-events 完整配置、事件类型表、systemd 示例 |

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

- ⛔ **禁止在日志/stderr 中打印 `GERRIT_HTTP_PASSWORD`、`GERRIT_HOOK_TOKEN` 或任何凭据字段**：不论任何异常情况
- ⛔ **禁止将凭据硬编码在脚本中**：必须通过环境变量传入
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
