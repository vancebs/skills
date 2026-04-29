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

### 2. Read Credentials (Config File or Environment Variables)

Credentials are loaded with the following priority (highest first):

1. **Config file** — `atlassian_config.json` in the current working directory
2. **Environment variables** — fallback when no config file is present

This allows multiple agents to each maintain their own `atlassian_config.json` with separate accounts without conflicting environment variables.

#### Config File Format (`atlassian_config.json`)

```json
{
  "jira": {
    "url": "https://jira.example.com",
    "token": "your-pat-token",
    "username": "user@example.com"
  },
  "confluence": {
    "url": "https://confluence.example.com",
    "token": "your-pat-token",
    "username": "user@example.com"
  }
}
```

- `username` is only required for Atlassian Cloud (`.atlassian.net` URLs); omit for Data Center / Server.
- The config file is never committed — add `atlassian_config.json` to `.gitignore`.

#### Credential Loading Helper

Always use this helper at the top of every script. It reads the config file first, then falls back to environment variables:

```python
import os
import json

def load_atlassian_config():
    """Load credentials from atlassian_config.json (priority) or environment variables."""
    config = {}
    config_path = os.path.join(os.getcwd(), "atlassian_config.json")
    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    def _get(section, key, env_var):
        return config.get(section, {}).get(key) or os.environ.get(env_var)

    return {
        "JIRA_URL":           _get("jira",       "url",      "JIRA_URL"),
        "JIRA_PAT_TOKEN":     _get("jira",       "token",    "JIRA_PAT_TOKEN"),
        "JIRA_USERNAME":      _get("jira",       "username", "JIRA_USERNAME"),
        "CONFLUENCE_URL":     _get("confluence", "url",      "CONFLUENCE_URL"),
        "CONFLUENCE_PAT_TOKEN": _get("confluence", "token",  "CONFLUENCE_PAT_TOKEN"),
        "CONFLUENCE_USERNAME":  _get("confluence", "username", "CONFLUENCE_USERNAME"),
    }

creds = load_atlassian_config()
JIRA_URL            = creds["JIRA_URL"]
JIRA_PAT_TOKEN      = creds["JIRA_PAT_TOKEN"]
JIRA_USERNAME       = creds["JIRA_USERNAME"]
CONFLUENCE_URL      = creds["CONFLUENCE_URL"]
CONFLUENCE_PAT_TOKEN = creds["CONFLUENCE_PAT_TOKEN"]
CONFLUENCE_USERNAME  = creds["CONFLUENCE_USERNAME"]
```

If any required credential is missing after both sources are checked, surface a clear error message.

### 3. Initialize Clients

**PAT token authentication** (Data Center / Server):
```python
from atlassian import Jira, Confluence

jira = Jira(url=JIRA_URL, token=JIRA_PAT_TOKEN)
confluence = Confluence(url=CONFLUENCE_URL, token=CONFLUENCE_PAT_TOKEN)
```

**Atlassian Cloud** (if URL contains `.atlassian.net`):
```python
# Cloud uses username + API token (not PAT)
jira = Jira(url=JIRA_URL, username=JIRA_USERNAME, password=JIRA_PAT_TOKEN, cloud=True)
confluence = Confluence(url=CONFLUENCE_URL, username=CONFLUENCE_USERNAME, password=CONFLUENCE_PAT_TOKEN, cloud=True)
```

Auto-detect which mode to use:
```python
def is_cloud(url: str) -> bool:
    return "atlassian.net" in url

def get_jira():
    if not JIRA_URL or not JIRA_PAT_TOKEN:
        raise EnvironmentError(
            "Jira credentials missing. Set 'jira.url' and 'jira.token' in atlassian_config.json "
            "or set JIRA_URL and JIRA_PAT_TOKEN environment variables."
        )
    if is_cloud(JIRA_URL):
        return Jira(url=JIRA_URL, username=JIRA_USERNAME or "", password=JIRA_PAT_TOKEN, cloud=True)
    return Jira(url=JIRA_URL, token=JIRA_PAT_TOKEN)

def get_confluence():
    if not CONFLUENCE_URL or not CONFLUENCE_PAT_TOKEN:
        raise EnvironmentError(
            "Confluence credentials missing. Set 'confluence.url' and 'confluence.token' in atlassian_config.json "
            "or set CONFLUENCE_URL and CONFLUENCE_PAT_TOKEN environment variables."
        )
    if is_cloud(CONFLUENCE_URL):
        return Confluence(url=CONFLUENCE_URL, username=CONFLUENCE_USERNAME or "", password=CONFLUENCE_PAT_TOKEN, cloud=True)
    return Confluence(url=CONFLUENCE_URL, token=CONFLUENCE_PAT_TOKEN)
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

1. **Check credentials** — load from `atlassian_config.json` first, then env vars; fail fast with a helpful message if missing
2. **Install SDK** if not present (`pip install atlassian-python-api`)
3. **Write a Python script** using the patterns in the reference files
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
new_issue = jira.create_issue(fields=fields)
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
- `scripts/setup_check.py` — verifies credentials (config file + env vars) and SDK installation
- `scripts/atlassian_config.json.example` — config file template (copy to your agent's working dir as `atlassian_config.json`)
