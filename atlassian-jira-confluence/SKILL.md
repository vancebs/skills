---
name: atlassian-jira-confluence
description: "Use this skill whenever the user wants to interact with Jira or Confluence. This includes creating, reading, updating, or deleting Jira issues, projects, sprints, boards, components, versions, attachments, comments, worklogs, users, groups, or permissions. Also use for any Confluence operation: pages, spaces, labels, attachments, templates, whiteboards, comments, search (CQL), or space permissions. Trigger on phrases like 'create a Jira issue', 'update Confluence page', 'search issues with JQL', 'add comment to ticket', 'get sprint info', 'list Confluence spaces', 'export page as PDF', or any request involving Atlassian tools. Always invoke this skill before answering Jira or Confluence questions, even if the user does not explicitly say 'use the skill'."
---

# Atlassian Jira & Confluence Skill

**What this skill does:** Create, read, update, and delete Jira issues/projects/sprints/boards and Confluence pages/spaces/attachments using the `atlassian-python-api` SDK.

**Requires:** Python 3 + `pip install atlassian-python-api` (run once)

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

> 注意：此 skill 通过 copy-paste 代码片段使用，不直接调用 skill 内的脚本，因此 `SKILL_DIR` 不影响日常使用。如果 agent 平台会自动设置 `SKILL_DIR`，则代码块中的 `_skill_dir()` 会自动生效。

```bash
# Linux / macOS — 检测并设置 SKILL_DIR（可选）
export SKILL_DIR=$(python3 -c "
import os, sys
from pathlib import Path
name = 'atlassian-jira-confluence'
ws = Path(os.environ.get('SKILL_WORKSPACE', os.getcwd()))
for p in [ws/'.agents'/'skills'/name, Path.home()/'.agents'/'skills'/name]:
    if p.is_dir():
        print(p); sys.exit(0)
sys.exit(1)
") 2>/dev/null || true
```

---

## ✅ Setup Checklist

Complete these steps once before using the skill.

### Step 1 — Install SDK

```bash
pip install atlassian-python-api
# or: python -m pip install atlassian-python-api
```

It's safe to run multiple times.

### Step 2 — Create Config File

```bash
# Linux / macOS
mkdir -p "$SKILL_WORKSPACE/config/atlassian-jira-confluence"

# Windows CMD
mkdir "%SKILL_WORKSPACE%\config\atlassian-jira-confluence"
```

Create `config/atlassian-jira-confluence/.atlassian.json`:

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

> **Note:** `username` is only required for Atlassian Cloud (`.atlassian.net` URLs).
>
> **Tokens:** Generate at Jira/Confluence → Profile → Personal Access Tokens (Data Center), or Atlassian account settings → API tokens (Cloud).

Add to `.gitignore`:
```
config/atlassian-jira-confluence/.atlassian.json
```

### Step 3 — Test the Connection

```python
# Save as test_connection.py and run: python test_connection.py
import sys, os
sys.path.insert(0, os.environ.get("SKILL_WORKSPACE", "."))
from atlassian import Jira

# (paste get_jira() helper below here, or copy from the Initialize Clients section)
jira = get_jira()
print(jira.myself())
```

---

## ⚡ Quick Reference

| Task | SDK call |
|---|---|
| Create issue | `jira.issue_create(fields={...})` |
| Get issue | `jira.issue("PROJ-123")` |
| Update issue | `jira.update_issue_field("PROJ-123", fields={...})` |
| Transition issue | `jira.transition_issue("PROJ-123", "Done")` |
| JQL search | `jira.jql("project=PROJ AND status='Open'", limit=50)` |
| Add comment | `jira.add_comment("PROJ-123", "Comment text")` |
| Create Confluence page | `confluence.create_page("SPACE", "Title", "<p>Body</p>")` |
| Get page by title | `confluence.get_page_by_title("SPACE", "Title")` |
| Update page | `confluence.update_page(page_id, "Title", "<p>New body</p>")` |
| Search Confluence (CQL) | `confluence.cql('space="SPACE" AND text~"keyword"', limit=20)` |

---

## 📋 Task Workflows

### Workflow A — Triage / Update a Jira Issue (Step-by-Step Checklist)

- [ ] 1. Set workspace: `export SKILL_WORKSPACE="$(pwd)"`
- [ ] 2. Install SDK if needed: `pip install atlassian-python-api`
- [ ] 3. Copy the **Initialize Clients** code block below into your script
- [ ] 4. Search for issues:
  ```python
  issues = jira.jql("project = PROJ AND status = 'To Do' ORDER BY priority DESC", limit=20)
  for issue in issues.get("issues", []):
      print(issue["key"], issue["fields"]["summary"])
  ```
- [ ] 5. Get full details of a specific issue:
  ```python
  issue = jira.issue("PROJ-123")
  print(issue["fields"]["status"]["name"])
  ```
- [ ] 6. Update a field:
  ```python
  jira.update_issue_field("PROJ-123", fields={"priority": {"name": "High"}})
  ```
- [ ] 7. Transition to new status:
  ```python
  jira.transition_issue("PROJ-123", "In Progress")
  ```
- [ ] 8. Add a comment:
  ```python
  jira.add_comment("PROJ-123", "Investigating root cause.")
  ```

---

### Workflow B — Create / Update a Confluence Page (Step-by-Step Checklist)

- [ ] 1. Set workspace: `export SKILL_WORKSPACE="$(pwd)"`
- [ ] 2. Copy the **Initialize Clients** code block below into your script
- [ ] 3. Find the target space key (list all spaces):
  ```python
  spaces = confluence.get_all_spaces(start=0, limit=50)
  for s in spaces.get("results", []):
      print(s["key"], s["name"])
  ```
- [ ] 4. Check if the page already exists:
  ```python
  page = confluence.get_page_by_title("MYSPACE", "My Page Title")
  ```
- [ ] 5a. If page does NOT exist — create it:
  ```python
  result = confluence.create_page(
      space="MYSPACE",
      title="My Page Title",
      body="<p>Content in storage format.</p>",
      parent_id=None,   # or a parent page ID
  )
  print(result["id"], result["_links"]["webui"])
  ```
- [ ] 5b. If page EXISTS — update it:
  ```python
  page_id = page["id"]
  confluence.update_page(page_id, "My Page Title", "<p>Updated content.</p>")
  ```
- [ ] 6. (Optional) Add a label:
  ```python
  confluence.set_page_label(page_id, "my-label")
  ```

---

## Initialize Clients (Copy-Paste This Into Your Script)

Always use this code block so config-file priority is respected automatically.

```python
import os
import json
from pathlib import Path
from atlassian import Jira, Confluence


_SKILL_NAME = "atlassian-jira-confluence"
_CONFIG_FILENAME = ".atlassian.json"


def _workspace() -> Path:
    """Return the agent's project workspace directory (for config / output files).

    Reads SKILL_WORKSPACE env var first — stays correct even when the calling
    process cd's into subdirectories mid-session.
    Falls back to cwd() for backward compatibility.
    """
    ws = os.environ.get("SKILL_WORKSPACE", "").strip()
    return Path(ws).resolve() if ws else Path(os.getcwd())


def _skill_dir() -> Path:
    """Return this skill's installation directory (for own scripts / assets).

    Priority: SKILL_DIR env var (set by platform) > Path(__file__) derivation.
    This is DISTINCT from _workspace(), which is the agent's project directory.
    """
    sd = os.environ.get("SKILL_DIR", "").strip()
    if sd:
        return Path(sd).resolve()
    # When this code is copy-pasted into an agent-generated script, __file__
    # points to that script's location — not the skill dir.  SKILL_DIR env var
    # is the reliable source; fall back gracefully.
    return Path(__file__).resolve().parent


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

    {workspace} = SKILL_WORKSPACE env var, or cwd when the script was started.
    """
    workspace = _workspace()
    skill_dir = _skill_dir()
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
    return str(_workspace() / "config" / _SKILL_NAME / _CONFIG_FILENAME)


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

## Configuration Reference

### Config File Search Order (Highest Priority First)

| Priority | Path | Notes |
|---|---|---|
| 1 ✅ preferred | `{workspace}/config/atlassian-jira-confluence/.atlassian.json` | Create here |
| 2 | `{workspace}/config/.atlassian.json` | |
| 3 | `{workspace}/.atlassian.json` | |
| 4 | `{skill-dir}/.atlassian.json` | Dev/testing fallback |
| 5 | `$HOME/.config/atlassian-jira-confluence/.atlassian.json` | Per-user |
| 6 | `$HOME/.config/.atlassian.json` | |
| 7 | `$HOME/.atlassian.json` | |

`{workspace}` = value of `SKILL_WORKSPACE` env var, or `cwd()` at script start.

### Environment Variables (fallback when no config file)

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

---

## Execution Rules (Important for All Models)

1. **Always call `load_config()` at the start** — it automatically checks all 7 config paths.

2. **Handle errors gracefully:**
   ```python
   from atlassian.errors import ApiError
   try:
       result = jira.issue("PROJ-123")
   except ApiError as e:
       print(f"API error {e.status_code}: {e.reason}")
   except Exception as e:
       print(f"Error: {e}")
   ```

---

## Jira Operations Reference

Full reference: `references/jira-operations.md`

| Category | Operations |
|---|---|
| Issues | create, read, update, delete, transition, link, clone, archive |
| Search | JQL queries, CQL autocomplete, CSV export |
| Comments & Worklogs | add/edit/delete comments, log time |
| Attachments | upload files, download all |
| Projects | CRUD, components, versions, issue types, permissions |
| Boards & Sprints | Agile boards, sprint management, backlog |
| Users & Groups | lookup, create groups, manage membership |
| Epics | epic issues, move to backlog |
| Admin | reindex, permissions, application properties, custom fields |

## Confluence Operations Reference

Full reference: `references/confluence-operations.md`

| Category | Operations |
|---|---|
| Pages | create, read, update, delete, move, append, export as PDF |
| Spaces | list, get, archive, permissions, export |
| Attachments | upload file/content, download, delete, version history |
| Labels | add/remove labels on pages |
| Comments | add inline and page-level comments |
| Templates | create, update, list, delete global/space templates |
| Whiteboards | create, get, delete (Cloud only) |
| Search (CQL) | full-text and structured search |
| Permissions | space-level for users, groups, anonymous |
| Properties | set/get/delete page properties and inline task checkboxes |

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

## ⛔ 约束与禁止事项

### 不支持的场景

| 场景 | 原因 | 处理动作 |
|---|---|---|
| HTTP 401 Unauthorized | token / 密码错误或已过期 | 终止并提示用户重新生成 API token；**不重试** |
| HTTP 403 Forbidden | 账号无该操作权限 | 终止并提示用户联系管理员授权；**不重试** |
| HTTP 404 Not Found | Issue key / page ID / space key 不存在 | 终止当前操作，输出明确错误；不继续依赖该资源的后续步骤 |
| HTTP 429 Rate Limited | 请求频率超限 | 等待响应头 `Retry-After` 秒数后重试一次；仍失败则终止 |
| HTTP 5xx Server Error | 服务端故障 | 最多重试 3 次（指数退避 1s/2s/4s），超限后输出错误并终止 |
| 响应体非 JSON / 解析失败 | 代理层返回 HTML 错误页 | 输出原始响应前 200 字符，提示用户检查 `url` 配置 |
| 创建页面时父页面不存在 | parent_id 无效 | 先调用 `confluence.get_page_by_id(parent_id)` 验证存在，不存在则停止并提示 |
| JQL / CQL 语法错误 | 查询字符串格式错误 | 捕获 `ApiError(400)`，输出错误信息，提示用户修正查询语法 |
| 并发编辑 Confluence 页面（版本冲突） | 另一用户同时编辑 | 捕获 `ApiError(409)`，获取最新版本号后重试一次；仍冲突则停止并提示 |
| 附件大小超过实例限制（通常 50–250 MB）| 服务端拒绝 | 上传前检查文件大小；超过 50 MB 时提示用户确认服务端限制 |

### 明确禁止的操作

- ⛔ **禁止硬编码 `url`, `username`, `api_token`**：必须从配置文件或环境变量读取
- ⛔ **禁止将 `.atlassian.json`（含 token 的配置文件）提交到 Git**：必须加入 `.gitignore`
- ⛔ **禁止在日志/输出中打印 `api_token` 或 `password`**：不论任何错误情况
- ⛔ **禁止在没有 `.atlassian.json` 或环境变量时静默使用空凭据运行**：必须 exit 1 并提示配置
- ⛔ **禁止 `delete` 操作不经用户确认**：删除 Jira issue、Confluence page、space 前必须在报告中列明将要删除的内容，等待用户确认

### 边界条件

| 参数 | 范围 | 超限行为 |
|---|---|---|
| JQL / CQL `limit` | 1–1000；推荐 ≤ 100 | 超过 1000 → 截断为 1000，记录 WARNING |
| Confluence page body 大小 | 推荐 < 5 MB | 超过 5 MB → 警告用户，发布可能超时 |
| 附件文件大小 | ≤ 50 MB（默认实例限制）| 超限前提示用户；不自动分块上传 |
| JQL 字符串长度 | ≤ 32768 字符 | 超限 → 截断并输出 WARNING |

### 幂等性声明

| 操作 | 幂等性 | 说明 |
|---|---|---|
| `jira.issue()`, `confluence.get_page_by_id()` | ✅ 幂等 | 只读操作 |
| `jira.issue_create()`, `confluence.create_page()` | ❌ 非幂等 | 重复调用会创建重复条目；调用方负责先检查是否存在 |
| `jira.issue_update()`, `confluence.update_page()` | ⚠️ 非幂等（有版本保护）| 需传入正确版本号（`version.number`）；否则返回 409 |
| `jira.transition_issue()` | ⚠️ 非幂等（有保护） | Jira 会拒绝已处于目标状态的转换（返回 400） |

---

For the complete API reference with all method signatures, see:
- `references/jira-operations.md`
- `references/confluence-operations.md`
- `scripts/setup_check.py` — verifies environment and SDK installation
