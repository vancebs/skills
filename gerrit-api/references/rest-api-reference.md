# Gerrit REST API Reference

> **来源：** gerrit-api skill 参考文件。查看 REST API 端点、认证方式、直接 HTTP 操作时参考本文档。

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

Use `gerrit_api.py` for most tasks. Use direct HTTP only for operations not covered by the script.

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


## ⚡ Quick Reference — REST API Commands

All commands follow the pattern: `python3 scripts/gerrit_api.py <command> [args]`

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
