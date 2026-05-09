---
name: atlassian-jira-confluence
description: "Use this skill whenever the user wants to interact with Jira or Confluence. This includes creating, reading, updating, or deleting Jira issues, projects, sprints, boards, components, versions, attachments, comments, worklogs, users, groups, or permissions. Also use for any Confluence operation: pages, spaces, labels, attachments, templates, whiteboards, comments, search (CQL), or space permissions. Trigger on phrases like 'create a Jira issue', 'update Confluence page', 'search issues with JQL', 'add comment to ticket', 'get sprint info', 'list Confluence spaces', 'export page as PDF', or any request involving Atlassian tools. Always invoke this skill before answering Jira or Confluence questions, even if the user does not explicitly say 'use the skill'."
---

# Atlassian Jira & Confluence Skill

Interact with Jira and Confluence using the `atlassian-python-api` SDK. This skill covers all SDK-supported operations for both platforms.

## Setup

### 1. Install the SDK (if not already installed)

Run this first — it's safe to run multiple times:

```bash
pip install atlassian-python-api
```

On Windows (CMD or PowerShell), `pip` and `python` should both work. If `pip` isn't on PATH, try `python -m pip install atlassian-python-api`.

### 2. Configure Credentials

Credentials can be provided via a **config file** (preferred) or **environment variables**. The config file always takes priority over environment variables when both are present.

#### Option A: Config File (takes priority)

The config file is searched in the following priority order (highest first):

| Priority | Path |
|---|---|
| 1 (**preferred**) | `{workspace}/config/atlassian-jira-confluence/.atlassian.json` |
| 2 | `{workspace}/config/.atlassian.json` |
| 3 | `{workspace}/.atlassian.json` |
| 4 | `{skill-dir}/.atlassian.json` *(dev/testing fallback)* |
| 5 | `$HOME/.config/atlassian-jira-confluence/.atlassian.json` |
| 6 | `$HOME/.config/.atlassian.json` |
| 7 | `$HOME/.atlassian.json` |

`{workspace}` is the current working directory. **Always create the config at the highest-priority path** so agents find it without extra configuration.

```bash
# Create config at the recommended location
mkdir -p config/atlassian-jira-confluence
# then fill in the file below
```

```json
{
  "confluence": {
    "url": "https://your-confluence.example.com",
    "token": "your-pat-token",
    "username": "you@example.com"
  },
  "jira": {
    "url": "https://your-jira.example.com",
    "token": "your-pat-token",
    "username": "you@example.com"
  }
}
```

> `username` is only required for Atlassian Cloud (`.atlassian.net` URLs) — use your email address.

#### Option B: Environment Variables

Never ask the user to paste tokens into code. Read them only via `os.environ`.

```bash
# Confluence
export CONFLUENCE_URL=https://your-confluence.example.com
export CONFLUENCE_PAT_TOKEN=your-pat-token
export CONFLUENCE_USERNAME=you@example.com   # Cloud only

# Jira
export JIRA_URL=https://your-jira.example.com
export JIRA_PAT_TOKEN=your-pat-token
export JIRA_USERNAME=you@example.com          # Cloud only
```

Windows CMD: `set VAR=value` | PowerShell: `$env:VAR = "value"`

### 3. Initialize Clients

Always use the `load_config()` + helper functions below so that the config-file-first priority is respected automatically.

```python
import os
import json
from pathlib import Path
from atlassian import Jira, Confluence


_SKILL_NAME = "atlassian-jira-confluence"
_CONFIG_FILENAME = ".atlassian.json"


def load_config() -> dict:
    """Return credentials dict from the first config file found, or {}.

    Search priority (highest first):
      1. {workspace}/config/atlassian-jira-confluence/.atlassian.json
      2. {workspace}/config/.atlassian.json
      3. {workspace}/.atlassian.json
      4. {skill-dir}/.atlassian.json
      5. $HOME/.config/atlassian-jira-confluence/.atlassian.json
      6. $HOME/.config/.atlassian.json
      7. $HOME/.atlassian.json
    """
    workspace = Path(os.getcwd())
    skill_dir = Path(__file__).resolve().parent  # adjust if script location differs
    home = Path.home()

    candidates = [
        workspace / "config" / _SKILL_NAME / _CONFIG_FILENAME,
        workspace / "config" / _CONFIG_FILENAME,
        workspace / _CONFIG_FILENAME,
        skill_dir / _CONFIG_FILENAME,
        home / ".config" / _SKILL_NAME / _CONFIG_FILENAME,
        home / ".config" / _CONFIG_FILENAME,
        home / _CONFIG_FILENAME,
    ]
    for path in candidates:
        if path.is_file():
            with open(path) as fh:
                return json.load(fh)
    return {}


def _preferred_config_path() -> str:
    return str(Path(os.getcwd()) / "config" / _SKILL_NAME / _CONFIG_FILENAME)


def is_cloud(url: str) -> bool:
    return "atlassian.net" in url


def get_jira():
    cfg = load_config().get("jira", {})
    url      = cfg.get("url")      or os.environ.get("JIRA_URL", "")
    token    = cfg.get("token")    or os.environ.get("JIRA_PAT_TOKEN", "")
    username = cfg.get("username") or os.environ.get("JIRA_USERNAME", "")
    if not url or not token:
        raise EnvironmentError(
            "Jira credentials missing.\n"
            f"  Config file : create {_preferred_config_path()} with 'jira.url' and 'jira.token'\n"
            "  Env vars    : set JIRA_URL and JIRA_PAT_TOKEN"
        )
    if is_cloud(url):
        return Jira(url=url, username=username, password=token, cloud=True)
    return Jira(url=url, token=token)


def get_confluence():
    cfg = load_config().get("confluence", {})
    url      = cfg.get("url")      or os.environ.get("CONFLUENCE_URL", "")
    token    = cfg.get("token")    or os.environ.get("CONFLUENCE_PAT_TOKEN", "")
    username = cfg.get("username") or os.environ.get("CONFLUENCE_USERNAME", "")
    if not url or not token:
        raise EnvironmentError(
            "Confluence credentials missing.\n"
            f"  Config file : create {_preferred_config_path()} with 'confluence.url' and 'confluence.token'\n"
            "  Env vars    : set CONFLUENCE_URL and CONFLUENCE_PAT_TOKEN"
        )
    if is_cloud(url):
        return Confluence(url=url, username=username, password=token, cloud=True)
    return Confluence(url=url, token=token)
```

---

## Windows Compatibility

When running scripts on Windows:
- Use `python` (not `python3`) unless the user specifies otherwise
- Path separators: use `os.path.join()` or raw strings `r"C:\path"` — never hardcode forward slashes in file paths
- In CMD: set env vars with `set JIRA_URL=https://...`
- In PowerShell: `$env:JIRA_URL = "https://..."`
- In Python scripts, `os.environ.get()` works identically on all platforms

---

## Jira Operations

See `references/jira-operations.md` for the full reference. Key categories:

- **Issues**: create, read, update, delete, transition, link, clone, archive
- **Search**: JQL queries, CQL autocomplete, CSV export
- **Comments & Worklogs**: add/edit/delete comments, log time
- **Attachments**: upload files, download all attachments
- **Projects**: CRUD, components, versions, issue types, permissions
- **Boards & Sprints**: Agile boards, sprint management, backlog
- **Users & Groups**: lookup, create groups, manage membership
- **Epics**: epic issues, move to backlog
- **Admin**: reindex, permissions, application properties, custom fields
- **Cluster/Health** (DC only): cluster nodes, health checks
- **Tempo**: worklog search

## Confluence Operations

See `references/confluence-operations.md` for the full reference. Key categories:

- **Pages**: create, read, update, delete, move, append, export as PDF
- **Spaces**: list, get, archive, permissions, export
- **Attachments**: upload file/content, download, delete, version history
- **Labels**: add/remove labels on pages
- **Comments**: add inline and page-level comments
- **Templates**: create, update, list, delete global/space templates
- **Whiteboards** (Cloud only): create, get, delete
- **Users & Groups**: lookup, password change, group membership
- **Search (CQL)**: full-text and structured search
- **Permissions**: space-level permissions for users, groups, anonymous
- **Properties**: set/get/delete page properties and inline task checkboxes

---

## Execution Pattern

When a user asks for a Jira/Confluence operation:

1. **Check credentials** — call `load_config()` first, fall back to env vars; fail fast with a helpful message if both are missing
2. **Install SDK** if not present (`pip install atlassian-python-api`)
3. **Write a Python script to a file** — **never use `python -c '...'` one-liners**. Python code often contains single quotes (dict keys, f-strings like `s['name']`) that break shell quoting when the one-liner is wrapped in single quotes. Always write to a `.py` file and run it.
4. **Run it** using `python` (or `python3` on Linux/Mac)
5. **Show results** — print structured output (JSON, table, or plain text as appropriate)
6. **Handle errors gracefully** — wrap API calls in try/except and surface the HTTP status and message

### Error Handling Template

```python
from atlassian.errors import ApiError

try:
    result = jira.issue("PROJ-123")
    print(result)
except ApiError as e:
    print(f"API error {e.status_code}: {e.reason}")
except Exception as e:
    print(f"Error: {e}")
```

---

## Quick Examples

### Create a Jira Issue
```python
fields = {
    "project": {"key": "PROJ"},
    "summary": "Fix login bug",
    "description": "Users cannot log in with SSO.",
    "issuetype": {"name": "Bug"},
    "priority": {"name": "High"},
}
new_issue = jira.issue_create(fields=fields)
print(new_issue["key"])
```

### JQL Search
```python
issues = jira.jql("project = PROJ AND status = 'In Progress' ORDER BY created DESC", limit=50)
for issue in issues.get("issues", []):
    print(issue["key"], issue["fields"]["summary"])
```

### Create a Confluence Page
```python
body = "<p>This is the page content in storage format.</p>"
result = confluence.create_page(
    space="MYSPACE",
    title="My New Page",
    body=body,
    parent_id=None,  # or pass a parent page ID
)
print(result["id"], result["_links"]["webui"])
```

### Search Confluence with CQL
```python
results = confluence.cql('space = "MYSPACE" AND type = page AND text ~ "deployment"', limit=20)
for item in results.get("results", []):
    print(item["title"], item["_links"]["webui"])
```

---

For the complete API reference with all method signatures, see:
- `references/jira-operations.md`
- `references/confluence-operations.md`
- `scripts/setup_check.py` — verifies environment and SDK installation
