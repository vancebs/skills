# Gerrit SSH Stream Events — Full Reference

> **来源：** gerrit-api skill 参考文件。查看 SSH stream-events 配置、事件类型、脚本参数时参考本文档。

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

SSH connection (override env vars):
  --host HOST           SSH hostname (overrides GERRIT_SSH_HOST / GERRIT_URL)
  --port PORT           SSH port (overrides GERRIT_SSH_PORT, default: 29418)
  --username USER       SSH username (overrides GERRIT_SSH_USERNAME / GERRIT_USERNAME)
  --key PATH            SSH private key path (overrides GERRIT_SSH_KEY)

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
                        (default: $WORKSPACE/events.outbox.jsonl)

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
Environment=GERRIT_URL=https://gerrit.example.com
Environment=GERRIT_USERNAME=john.doe
Environment=GERRIT_HTTP_PASSWORD=secret
Environment=GERRIT_WORKSPACE=/opt/gerrit-workspace
ExecStart=/usr/bin/python3 /home/user/.agents/skills/gerrit-api/scripts/gerrit_stream_events.py \
    --output ${GERRIT_WORKSPACE}/events.jsonl \
    --hook-url http://127.0.0.1:8443/events \
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
