---
name: gerrit-api
description: Interact with Gerrit Code Review via the REST API — query changes, fetch diffs, post reviews with labels and inline comments, and manage change lifecycle. Also supports real-time event streaming via SSH (stream-events).
license: Apache-2.0
compatibility: Requires git, curl, jq, and base64. Requires python3 (≥3.9) and ssh for stream-events. Optional python3 for URL encoding.
metadata:
  based-on: https://github.com/yurnov/gerrit-in-5-min (gerrit-review skill by @yurnov)
  keywords: [gerrit, code review, code review automation, developer tools, stream-events, ssh]
---

# Gerrit API Skill

This skill enables you to interact with a Gerrit Code Review instance through its REST API and real-time SSH event stream. Use it to query open changes, read diffs, post code reviews, manage change lifecycle (submit, abandon, restore), and **continuously listen for Gerrit events** (new patch sets, merges, comments, and more).

Compared to the upstream `gerrit-review` skill, this version adds **config file support** so that multiple agents can each maintain their own credentials without conflicting environment variables, and **SSH stream-events support** for real-time change processing.

## Prerequisites

### Credentials — Config File or Environment Variables

Credentials are loaded with the following priority (highest first):

1. **Config file** — `gerrit_config.json` in the current working directory
2. **Environment variables** — fallback when no config file is present

#### REST API credentials

| Credential | Config file key | Environment variable | Description |
|---|---|---|---|
| Base URL | `url` | `GERRIT_URL` | Base URL of the Gerrit instance (no trailing slash) |
| Username | `username` | `GERRIT_USERNAME` | HTTP username from Gerrit → Settings → Profile |
| HTTP password | `password` | `GERRIT_HTTP_PASSWORD` | Token from Gerrit → Settings → HTTP Credentials → Generate Password |

> [!IMPORTANT]
> The **HTTP password** is NOT the user's login password. It is a separate token generated in the Gerrit web UI under **Settings → HTTP Credentials → Generate Password**.

#### SSH stream-events credentials

| Credential | Config file key | Environment variable | Description |
|---|---|---|---|
| SSH host | `ssh_host` | `GERRIT_SSH_HOST` | Hostname for SSH (defaults to host extracted from `url`) |
| SSH port | `ssh_port` | `GERRIT_SSH_PORT` | SSH port (default: `29418`) |
| SSH username | `ssh_username` | `GERRIT_SSH_USERNAME` | SSH username (defaults to `username`) |
| SSH key | `ssh_key` | `GERRIT_SSH_KEY` | Path to SSH private key (optional; uses SSH agent/default keys if absent) |

> [!IMPORTANT]
> The SSH user's public key must be uploaded to Gerrit under **Settings → SSH Keys**. The Gerrit SSH port is usually **29418** (not 22).

#### Config File (`gerrit_config.json`)

The config file is searched in the following priority order (highest first):

| Priority | Path |
|---|---|
| 1 (**preferred**) | `{workspace}/config/gerrit-api/gerrit_config.json` |
| 2 | `{workspace}/config/gerrit_config.json` |
| 3 | `{workspace}/gerrit_config.json` |
| 4 | `{skill-dir}/gerrit_config.json` *(dev/testing fallback)* |
| 5 | `$HOME/.config/gerrit-api/gerrit_config.json` |
| 6 | `$HOME/.config/gerrit_config.json` |
| 7 | `$HOME/gerrit_config.json` |

`{workspace}` is the current working directory. **Always create the config at the highest-priority path** so all gerrit-api scripts find it without extra arguments.

```bash
# Create config at the recommended location
mkdir -p config/gerrit-api
cp /path/to/gerrit-api/scripts/gerrit_config.json.example config/gerrit-api/gerrit_config.json
# then edit config/gerrit-api/gerrit_config.json with real values
```

```json
{
  "url": "https://gerrit.example.com",
  "username": "john.doe",
  "password": "your-http-credential-token",
  "ssh_host": "gerrit.example.com",
  "ssh_port": 29418,
  "ssh_username": "john.doe",
  "ssh_key": "~/.ssh/id_rsa",
  "hook_url": "http://127.0.0.1:8443/events",
  "hook_token": "your-hook-token",
  "outbox_path": ""
}
```

The SSH and hook fields are optional. `ssh_host` is inferred from `url` when absent. `hook_url` / `hook_token` / `outbox_path` can also be provided via `--hook-url` / `--hook-token` / `--outbox` CLI flags or `HOOK_URL` / `HOOK_TOKEN` / `OUTBOX_PATH` env vars.

- Config file values take **priority** over environment variables.
- Add `config/gerrit-api/gerrit_config.json` to `.gitignore` — never commit credentials.
- Each agent running in a different working directory can have its own config file.

#### Environment Variables (fallback)

When no config file is present, credentials come from environment variables:

```bash
# Linux/macOS
export GERRIT_URL="https://gerrit.example.com"
export GERRIT_USERNAME="john.doe"
export GERRIT_HTTP_PASSWORD="your-http-credential-token"
export GERRIT_SSH_HOST="gerrit.example.com"   # optional; derived from GERRIT_URL
export GERRIT_SSH_PORT="29418"                 # optional; default 29418
export GERRIT_SSH_USERNAME="john.doe"          # optional; defaults to GERRIT_USERNAME
export GERRIT_SSH_KEY="~/.ssh/id_rsa"          # optional
# Hook delivery (optional)
export HOOK_URL="http://127.0.0.1:8443/events"
export HOOK_TOKEN="your-hook-token"
export OUTBOX_PATH="/var/log/gerrit/events.outbox.jsonl"
```

### Tools

- `python3` (≥ 3.9) — used for all scripts (`gerrit_api.py`, `gerrit_stream_events.py`)
- `ssh` — used by the stream-events listener to connect to Gerrit

## Quick Start

Use the cross-platform helper script at `scripts/gerrit_api.py` for REST API operations.

```bash
# Query open changes
python scripts/gerrit_api.py query "status:open+limit:5"

# Get change details
python scripts/gerrit_api.py get-change 12345

# List files changed in a revision
python scripts/gerrit_api.py list-files 12345

# Get a file diff
python scripts/gerrit_api.py get-diff 12345 "src/main/App.java"

# Get raw file content
python scripts/gerrit_api.py get-content 12345 "src/main/App.java"

# Post a draft comment on a specific line
python scripts/gerrit_api.py create-draft 12345 current '{"path":"src/main/App.java","line":23,"message":"Consider renaming this.","unresolved":true}'

# Post a review with a Code-Review +1 label
python scripts/gerrit_api.py review 12345 current '{"message":"Looks good!","labels":{"Code-Review":1}}'

# Submit a change
python scripts/gerrit_api.py submit 12345

# Abandon a change
python scripts/gerrit_api.py abandon 12345
```

## SSH Stream Events

Gerrit exposes a real-time event feed over SSH via `gerrit stream-events`. Use `scripts/gerrit_stream_events.py` to subscribe to this feed, parse each event, and act on it continuously.

### How it works

1. The script opens an SSH connection to the Gerrit server on port 29418 (or `ssh_port`).
2. It runs `gerrit stream-events` on the server.
3. Gerrit emits one JSON object per line for every repository event.
4. The script parses each line, enriches it with a `summary` string and `_received_at` timestamp, optionally filters by event type / project / branch, and writes to stdout (and optionally a log file).

### Quick Start — Stream Events

```bash
# Make executable (one-time)
chmod +x scripts/gerrit_stream_events.py

# Stream all events (Ctrl+C to stop)
python3 scripts/gerrit_stream_events.py

# Pretty-print only new patch-set uploads and merges
python3 scripts/gerrit_stream_events.py \
  --filter patchset-created,change-merged \
  --pretty

# Show one-line human-readable summaries
python3 scripts/gerrit_stream_events.py --summary

# Collect 20 events then exit (useful for testing)
python3 scripts/gerrit_stream_events.py --max-events 20

# Run for 5 minutes, log to file, auto-reconnect on drop
python3 scripts/gerrit_stream_events.py \
  --timeout 300 \
  --output gerrit_events.jsonl \
  --reconnect

# Filter to a specific project and branch, pipe to jq
python3 scripts/gerrit_stream_events.py \
  --filter patchset-created \
  --project myOrg/myProject \
  --branch main \
  | jq '{type, change: .change.number, subject: .change.subject, uploader: .uploader.name}'
```

### Agent Patterns

See the **Script Options Reference → Updated Agent Patterns** section below for full examples (Patterns A–D).

For a quick pipe-based approach:

```bash
python3 scripts/gerrit_stream_events.py \
  --filter patchset-created \
  | while IFS= read -r event; do
      CHANGE=$(echo "$event" | python3 -c "import sys,json; e=json.load(sys.stdin); print(e['change']['number'])")
      echo "New patch set on change $CHANGE"
    done
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

Every event emitted by the script has these additional fields added:

| Field | Description |
|---|---|
| `_received_at` | ISO 8601 UTC timestamp when the agent received the event |
| `summary` | Human-readable one-line description of the event |

**Example parsed event** (`patchset-created`):

```json
{
  "type": "patchset-created",
  "change": {
    "project": "myOrg/myProject",
    "branch": "main",
    "id": "Iabc123...",
    "number": 12345,
    "subject": "Fix null pointer in UserService",
    "owner": { "name": "Alice", "email": "alice@example.com" },
    "url": "https://gerrit.example.com/c/myOrg/myProject/+/12345",
    "commitMessage": "Fix null pointer in UserService\n\nChange-Id: Iabc123...\n",
    "status": "NEW"
  },
  "patchSet": {
    "number": 2,
    "revision": "deadbeef...",
    "parents": ["cafebabe..."],
    "ref": "refs/changes/45/12345/2",
    "uploader": { "name": "Alice" },
    "author": { "name": "Alice" },
    "sizeInsertions": 10,
    "sizeDeletions": -3
  },
  "uploader": { "name": "Alice", "email": "alice@example.com", "username": "alice" },
  "eventCreatedOn": 1715000000,
  "_received_at": "2025-05-06T12:00:00Z",
  "summary": "2025-05-06T12:00:00Z patchset-created: Alice uploaded ps2 to [myOrg/myProject/main #12345] 'Fix null pointer in UserService'"
}
```

### Script Options Reference

```
python3 scripts/gerrit_stream_events.py [options]

Config:
  --config FILE         Config file (searches 7 default locations if omitted)

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
                        (default: <workspace>/events.outbox.jsonl)

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

When `--hook-url` is set, each accepted event is **POSTed** as JSON (same payload written to the JSONL file) to that URL.

#### Request format

```
POST /your-path HTTP/1.1
Content-Type: application/json
X-Auth-Token: <token>          ← only when --hook-token is set

{ "type": "patchset-created", "change": {...}, "_received_at": "...", "summary": "..." }
```

#### Response handling

| HTTP status | Behaviour |
|---|---|
| 2xx | Delivered — done |
| 4xx | Client error — **not retried** (bad token, wrong path, etc.) |
| 5xx / network error / timeout | **Retry** up to `--hook-retries` times with exponential back-off (base 0.5 s × 2ⁿ ± 10 % jitter), then write to outbox |

#### Outbox

Events that exhaust all retries are appended to the outbox file (JSONL, same atomic-append semantics) so they can be replayed later.  Default path: `<workspace>/events.outbox.jsonl`.

> [!WARNING]
> Only point `--hook-url` at `127.0.0.1` or a UNIX socket in production.  If you must reach an external host, use TLS and rotate the token regularly.

### Foreground / systemd Mode

The script never daemonises itself.  Run it under `nohup &`, `systemd`, `supervisord`, or any process manager.  A minimal systemd unit:

```ini
[Unit]
Description=Gerrit stream-events listener
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/gerrit/scripts/gerrit_stream_events.py \
    --output /var/log/gerrit/events.jsonl \
    --hook-url http://127.0.0.1:8443/events \
    --hook-token *** \
    --reconnect
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Updated Agent Patterns

#### Pattern A — Background listener + polling log file (updated)

```bash
# Start listener: write file + push to hook, reconnect automatically
python3 scripts/gerrit_stream_events.py \
  --output events.jsonl \
  --hook-url http://127.0.0.1:8443/events \
  --hook-token MY_TOKEN \
  --reconnect --quiet &

# Later: read new events (reads only complete lines ending with \n)
while IFS= read -r line; do
  TYPE=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin)['type'])")
  echo "Event: $TYPE"
done < events.jsonl
```

#### Pattern B — Bounded collection for batch processing

```bash
python3 scripts/gerrit_stream_events.py \
  --timeout 30 \
  --filter patchset-created,change-merged \
  > batch_events.jsonl

# Process results
python3 -c "
import json, sys
for line in sys.stdin:
    ev = json.loads(line)
    if ev['type'] == 'patchset-created':
        print(ev['change']['number'], ev['patchSet']['number'])
" < batch_events.jsonl
```

#### Pattern C — Dry-run debug (no writes)

```bash
python3 scripts/gerrit_stream_events.py \
  --dry-run --summary --max-events 10
```

#### Pattern D — Only hook, outbox as safety net

```bash
python3 scripts/gerrit_stream_events.py \
  --no-output \
  --hook-url http://127.0.0.1:8443/events \
  --hook-token MY_TOKEN \
  --outbox /var/log/gerrit/events.outbox.jsonl \
  --reconnect
```



### Changes and Patch Sets
- A **change** is a single reviewable unit (corresponds to one commit).
- Each update to a change creates a new **patch set** (a new commit with the same `Change-Id`).
- Changes live under `refs/changes/` refs in the Git repo.

### Change-Id
- A footer line in the commit message (`Change-Id: I<hex>`) that links commits to Gerrit changes.
- The `commit-msg` hook (installed from Gerrit) auto-generates this.

### Labels
- **Code-Review**: Typically −2 to +2. `+2` means approved.
- **Verified**: Typically −1 to +1. Usually set by CI.
- Label ranges and names are project-specific.

### Workflow
1. Push to `refs/for/<branch>` to create/update a change for review.
2. Reviewers add comments and vote via labels.
3. Amend the commit (`git commit --amend`) and re-push for new patch sets.
4. Once approvals are met, a committer submits the change.

## REST API Reference

### Authentication

All authenticated requests use the `/a/` prefix and HTTP Basic Auth:

```bash
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/changes/?q=status:open+limit:5"
```

### Output Format

Gerrit JSON responses start with an **XSSI prevention prefix** `)]}'` on the first line. You must strip it before parsing:

```bash
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/changes/?q=status:open" | tail -n +2 | jq .
```

### URL Encoding

Project names, file paths, and branch names in URLs must be URL-encoded. Forward slashes in project/file paths become `%2F`:

```
myOrg/myProject  →  myOrg%2FmyProject
src/main/App.java  →  src%2Fmain%2FApp.java
```

### Key Endpoints

#### 1. Query Changes

```
GET /a/changes/?q=<query>&n=<limit>&o=<option>
```

Common query operators:
- `status:open` / `status:merged` / `status:abandoned`
- `owner:self` / `reviewer:self`
- `project:<name>` / `branch:<name>`
- `is:watched` / `is:starred`
- `after:"2025-01-01"` / `before:"2025-12-31"`

Common `o` (option) parameters to include extra data:
- `CURRENT_REVISION` — include current revision info
- `DETAILED_LABELS` — include detailed label/vote info
- `DETAILED_ACCOUNTS` — include full account info
- `CURRENT_FILES` — include file list for current revision
- `MESSAGES` — include change messages

Example:
```bash
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/changes/?q=status:open+owner:self&n=10&o=CURRENT_REVISION&o=DETAILED_LABELS" \
  | tail -n +2 | jq .
```

#### 2. Get Change Details

```
GET /a/changes/<change-id>?o=CURRENT_REVISION&o=DETAILED_LABELS
```

The `<change-id>` can be:
- A numeric change number: `12345`
- The full triplet: `project~branch~Change-Id`
- Just the Change-Id: `I8473b95934b5732ac55d26311a706c9c2bde9940`

Example:
```bash
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/changes/12345?o=CURRENT_REVISION&o=DETAILED_LABELS&o=DETAILED_ACCOUNTS" \
  | tail -n +2 | jq .
```

#### 3. List Files in a Revision

```
GET /a/changes/<change-id>/revisions/<revision-id>/files/
```

Use `current` as `<revision-id>` for the latest patch set.

Example:
```bash
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/changes/12345/revisions/current/files/" \
  | tail -n +2 | jq .
```

Response is a map of file paths to `FileInfo` objects:
```json
{
  "/COMMIT_MSG": { "status": "A", "lines_inserted": 7, "size_delta": 551, "size": 551 },
  "src/main/App.java": { "lines_inserted": 5, "lines_deleted": 3, "size_delta": 98, "size": 23348 }
}
```

#### 4. Get File Diff

```
GET /a/changes/<change-id>/revisions/<revision-id>/files/<file-id>/diff
```

The `<file-id>` must be URL-encoded. Add `?intraline` for intraline differences.

Example:
```bash
FILE_PATH="src%2Fmain%2FApp.java"
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/changes/12345/revisions/current/files/$FILE_PATH/diff" \
  | tail -n +2 | jq .
```

Response is a `DiffInfo` entity with `content` array containing `ab` (common), `a` (deleted), and `b` (added) line arrays.

#### 5. Get File Content

```
GET /a/changes/<change-id>/revisions/<revision-id>/files/<file-id>/content
```

Returns **base64-encoded** file content.

Example:
```bash
FILE_PATH="src%2Fmain%2FApp.java"
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  "$GERRIT_URL/a/changes/12345/revisions/current/files/$FILE_PATH/content" \
  | base64 -d
```

#### 6. Post a Review (Set Labels, Comments)

```
POST /a/changes/<change-id>/revisions/<revision-id>/review
Content-Type: application/json
```

**ReviewInput** JSON body:

```json
{
  "message": "Overall review comment shown at the top",
  "labels": {
    "Code-Review": 1
  },
  "comments": {
    "src/main/App.java": [
      {
        "line": 23,
        "message": "Consider renaming this variable for clarity."
      },
      {
        "range": {
          "start_line": 50,
          "start_character": 0,
          "end_line": 55,
          "end_character": 20
        },
        "message": "This block should be refactored."
      }
    ]
  }
}
```

Label values (project-specific, typical):
- **Code-Review**: `-2` (reject), `-1` (looks wrong), `0` (no score), `+1` (looks good), `+2` (approved)
- **Verified**: `-1` (fails), `0` (no score), `+1` (verified)

Example:
```bash
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message":"Looks good to me!","labels":{"Code-Review":1}}' \
  "$GERRIT_URL/a/changes/12345/revisions/current/review" \
  | tail -n +2 | jq .
```

#### 7. Post a Draft Comment

```
PUT /a/changes/<change-id>/revisions/<revision-id>/drafts
Content-Type: application/json
```

**CommentInput** JSON body:

```json
{
  "path": "src/main/App.java",
  "line": 23,
  "message": "[nit] trailing whitespace",
  "unresolved": true
}
```

Example:
```bash
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{"path":"src/main/App.java","line":23,"message":"[nit] trailing whitespace","unresolved":true}' \
  "$GERRIT_URL/a/changes/12345/revisions/current/drafts" \
  | tail -n +2 | jq .
```

#### 8. Submit a Change

```
POST /a/changes/<change-id>/submit
```

Example:
```bash
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{}' \
  "$GERRIT_URL/a/changes/12345/submit" \
  | tail -n +2 | jq .
```

#### 9. Abandon / Restore a Change

```
POST /a/changes/<change-id>/abandon
POST /a/changes/<change-id>/restore
```

Both accept an optional JSON body with a `message` field:

```bash
# Abandon
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message":"Superseded by change 12346"}' \
  "$GERRIT_URL/a/changes/12345/abandon" \
  | tail -n +2 | jq .

# Restore
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message":"Re-opening for further review"}' \
  "$GERRIT_URL/a/changes/12345/restore" \
  | tail -n +2 | jq .
```

#### 10. Add Reviewer

```
POST /a/changes/<change-id>/reviewers
Content-Type: application/json
```

```json
{
  "reviewer": "jane.roe@example.com"
}
```

To add as CC instead of reviewer, add `"state": "CC"`.

Example:
```bash
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"reviewer":"jane.roe@example.com"}' \
  "$GERRIT_URL/a/changes/12345/reviewers" \
  | tail -n +2 | jq .
```

#### 11. Set Topic

```
PUT /a/changes/<change-id>/topic
Content-Type: application/json
```

Example:
```bash
curl -s --user "$GERRIT_USERNAME:$GERRIT_HTTP_PASSWORD" \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{"topic":"my-feature-branch"}' \
  "$GERRIT_URL/a/changes/12345/topic" \
  | tail -n +2 | jq .
```

## Code Review Workflow

### Step 1 — Find changes to review

```bash
python scripts/gerrit_api.py query "status:open+reviewer:self+-owner:self"
```

### Step 2 — Inspect a change

```bash
python scripts/gerrit_api.py get-change 12345
python scripts/gerrit_api.py list-files 12345
python scripts/gerrit_api.py get-diff 12345 "path/to/file.java"
```

### Step 3 — Post your review

**Option A: Incremental Drafts**

```bash
python scripts/gerrit_api.py create-draft 12345 current '{"path":"path/to/file.java","line":42,"message":"Consider using a constant here instead of a magic number.","unresolved":true}'

python scripts/gerrit_api.py review 12345 current '{
  "message": "I left a few comments on the implementation. Please take a look.",
  "labels": {"Code-Review": -1},
  "drafts": "PUBLISH"
}'
```

**Option B: Single Step Review**

```bash
python scripts/gerrit_api.py review 12345 current '{
  "message": "Overall the approach looks solid. A few suggestions below.",
  "labels": {"Code-Review": 1},
  "comments": {
    "path/to/file.java": [
      {"line": 42, "message": "Consider using a constant here instead of a magic number.", "unresolved": true},
      {"line": 65, "message": "Nice cleanup here.", "unresolved": false}
    ]
  }
}'
```

Additional `comments` fields:
- `notify` — notification level (`ALL`, `OWNER`, `NONE`; prefer `OWNER` to avoid spamming)
- `in_reply_to` — URL-encoded UUID of the comment being replied to
- `unresolved` — `true` for action-required comments, `false` for informational/optional nits
- `fix_suggestions` — list of suggested code fixes

### Step 4 — Submit when ready

```bash
python scripts/gerrit_api.py submit 12345
```

## Troubleshooting

| Problem | Solution |
|---|---|
| `HTTP 401 Unauthorized` | Check `GERRIT_USERNAME` and `GERRIT_HTTP_PASSWORD` (or config file). Re-generate the HTTP password in Gerrit Settings. |
| `HTTP 404 Not Found` | Verify the change number exists. Check `GERRIT_URL` has no trailing slash. |
| `HTTP 409 Conflict` | You may be trying to review a change edit, or submit a change that doesn't meet requirements. |
| Config file not loaded | The script searches 7 paths in priority order. Run `python scripts/gerrit_api.py help` to see the search order, and ensure the file is in one of those locations. |

## Awareness

- `GERRIT_URL` and `GERRIT_USERNAME` (or config file equivalents) can be used in output, but **never print** `GERRIT_HTTP_PASSWORD` or the `password` config field in logs or outputs.
- The HTTP credential token must be kept secure and used only for authentication in API calls.

## Files

- `scripts/gerrit_api.py` — REST API helper script (cross-platform, Python, no extra deps)
- `scripts/gerrit_stream_events.py` — SSH stream-events listener and event parser
- `scripts/gerrit_config.json.example` — config file template; copy to the recommended path

## References

- [Gerrit REST API Documentation](https://gerrit-review.googlesource.com/Documentation/rest-api.html)
- [Gerrit Changes REST API](https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html)
- [Gerrit Search Operators](https://gerrit-review.googlesource.com/Documentation/user-search.html)
- [Gerrit Stream Events (SSH)](https://gerrit-review.googlesource.com/Documentation/cmd-stream-events.html)
- [Gerrit SSH Commands](https://gerrit-review.googlesource.com/Documentation/cmd-index.html)
- [Gerrit in 5 Minutes](https://github.com/yurnov/gerrit-in-5-min) — original skill this is based on
