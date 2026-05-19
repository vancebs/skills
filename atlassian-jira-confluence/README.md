# atlassian-jira-confluence

## 功能简述

通过 `atlassian-python-api` SDK 与 Atlassian Jira 和 Confluence 进行全功能交互。支持 Jira 的 Issue 管理、项目管理、看板与 Sprint、用户与权限管理，以及 Confluence 的页面、空间、附件、评论、搜索等所有 SDK 覆盖的操作。兼容 Atlassian Cloud 和 Data Center/Server 部署。

---

## 配置

### 前置安装

```bash
pip install atlassian-python-api
```

### 配置方式（选一）

配置文件优先级高于环境变量。配置文件非必选——两种方式等价。

**方式 A — 配置文件（推荐）**

创建 `$SKILL_WORKSPACE/.config/atlassian-jira-confluence.json`（或 `~/.config/atlassian-jira-confluence.json`）：

```json
{
  "JIRA_URL": "https://your-jira.example.com",
  "JIRA_PAT_TOKEN": "your-pat-token",
  "JIRA_USERNAME": "you@example.com",
  "CONFLUENCE_URL": "https://your-confluence.example.com",
  "CONFLUENCE_PAT_TOKEN": "your-pat-token",
  "CONFLUENCE_USERNAME": "you@example.com"
}
```

> `*_USERNAME` 仅 Atlassian Cloud（`.atlassian.net`）需要，填写邮箱地址。

**方式 B — 环境变量**

```bash
export JIRA_URL="https://your-jira.example.com"
export JIRA_PAT_TOKEN="your-pat-token"
export JIRA_USERNAME="you@example.com"          # Cloud only
export CONFLUENCE_URL="https://your-confluence.example.com"
export CONFLUENCE_PAT_TOKEN="your-pat-token"
export CONFLUENCE_USERNAME="you@example.com"    # Cloud only
```

### 环境检测

```bash
python scripts/setup_check.py
```

### 初始化客户端（代码模板）

```python
import json, os
from pathlib import Path
from atlassian import Jira, Confluence


def _load_skill_config(skill_name: str) -> dict:
    """Load $SKILL_WORKSPACE/.config/{skill}.json or ~/.config/{skill}.json."""
    for p in [Path.cwd() / ".config" / f"{skill_name}.json",
              Path.home() / ".config" / f"{skill_name}.json"]:
        if p.is_file():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                return d if isinstance(d, dict) else {}
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def _is_cloud(url: str) -> bool:
    return "atlassian.net" in url


def get_jira():
    cfg   = _load_skill_config("atlassian-jira-confluence")
    url   = (cfg.get("JIRA_URL") or os.environ.get("JIRA_URL", "")).strip().rstrip("/")
    token = (cfg.get("JIRA_PAT_TOKEN") or os.environ.get("JIRA_PAT_TOKEN", "")).strip()
    user  = (cfg.get("JIRA_USERNAME") or os.environ.get("JIRA_USERNAME", "")).strip()
    if not url or not token:
        raise EnvironmentError("Jira credentials missing. See SKILL.md Setup Checklist.")
    if _is_cloud(url):
        return Jira(url=url, username=user, password=token, cloud=True)
    return Jira(url=url, token=token)


def get_confluence():
    cfg   = _load_skill_config("atlassian-jira-confluence")
    url   = (cfg.get("CONFLUENCE_URL") or os.environ.get("CONFLUENCE_URL", "")).strip().rstrip("/")
    token = (cfg.get("CONFLUENCE_PAT_TOKEN") or os.environ.get("CONFLUENCE_PAT_TOKEN", "")).strip()
    user  = (cfg.get("CONFLUENCE_USERNAME") or os.environ.get("CONFLUENCE_USERNAME", "")).strip()
    if not url or not token:
        raise EnvironmentError("Confluence credentials missing. See SKILL.md Setup Checklist.")
    if _is_cloud(url):
        return Confluence(url=url, username=user, password=token, cloud=True)
    return Confluence(url=url, token=token)
```

---

## 详细功能描述

### Jira 操作

#### Issue 管理

```python
jira = get_jira()

# 创建 Issue
jira.issue_create(fields={
    "project": {"key": "PROJ"},
    "summary": "Fix login bug",
    "issuetype": {"name": "Bug"},
    "description": "Steps to reproduce..."
})

# 读取 Issue
issue = jira.issue("PROJ-123")

# 更新 Issue
jira.update_issue_field("PROJ-123", {"summary": "Updated title"})

# 删除 Issue
jira.delete_issue("PROJ-123")

# 过渡状态（关闭、重新打开等）
transitions = jira.get_issue_transitions("PROJ-123")
jira.issue_transition("PROJ-123", "Done")

# 克隆 Issue
jira.issue_create(fields={**issue["fields"], "summary": "[Clone] " + issue["fields"]["summary"]})
```

#### JQL 搜索

```python
# 搜索 Issue
results = jira.jql("project = PROJ AND status = Open AND assignee = currentUser()")

# 带分页
results = jira.jql("project = PROJ", limit=50, start=0)

# 导出为 CSV
csv_data = jira.export_csv("project = PROJ AND created >= -7d")
```

#### 评论与工时

```python
# 添加评论
jira.issue_add_comment("PROJ-123", "This looks good!")

# 记录工时
jira.add_worklog("PROJ-123", timeSpent="2h", comment="Investigated the root cause")
```

#### 附件

```python
# 上传附件
jira.add_attachment("PROJ-123", "/path/to/file.log")
```

#### 项目管理

```python
# 列出项目
projects = jira.projects()

# 获取项目组件
components = jira.get_project_components("PROJ")

# 获取版本
versions = jira.get_project_versions("PROJ")
```

#### 看板与 Sprint

```python
# 列出看板
boards = jira.get_all_agile_boards()

# 获取活跃 Sprint
sprints = jira.get_all_sprints_from_board(board_id=1)

# 将 Issue 移入 Sprint
jira.add_issues_to_sprint(sprint_id=42, issue_keys=["PROJ-123"])
```

#### 用户与权限

```python
# 查找用户
users = jira.user_find_by_user_string(query="john")

# 获取用户组
groups = jira.get_user_groups("john.doe")
```

---

### Confluence 操作

#### 页面管理

```python
confluence = get_confluence()

# 创建页面
confluence.create_page(
    space="MYSPACE",
    title="My Page",
    body="<p>Hello World</p>"
)

# 读取页面内容
page = confluence.get_page_by_title(space="MYSPACE", title="My Page")

# 更新页面
confluence.update_page(
    page_id=page["id"],
    title="My Page",
    body="<p>Updated content</p>"
)

# 追加内容
confluence.append_page(page_id=page["id"], additional_page_string="<p>More content</p>")

# 导出为 PDF
confluence.get_page_as_pdf(page_id=page["id"])

# 移动页面
confluence.move_page(space_key="MYSPACE", title="My Page", target_title="New Parent")
```

#### 空间管理

```python
# 列出空间
spaces = confluence.get_all_spaces(start=0, limit=50)

# 获取空间信息
space = confluence.get_space("MYSPACE")
```

#### 附件

```python
# 上传附件
confluence.attach_file("/path/to/file.png", page_id=page["id"])

# 列出附件
attachments = confluence.get_attachments_from_content(page_id=page["id"])
```

#### 搜索（CQL）

```python
# 全文搜索
results = confluence.cql('type=page AND space="MYSPACE" AND text~"deployment"')
```

#### 评论

```python
# 添加页面评论
confluence.add_comment(page_id=page["id"], text="Please review section 3.")
```

#### 标签

```python
# 添加标签
confluence.set_page_label(page_id=page["id"], label="reviewed")

# 获取标签
labels = confluence.get_page_labels(page_id=page["id"])
```

#### 用户与权限

```python
# 查找用户
user = confluence.get_user_details_by_username("john.doe")

# 空间权限
confluence.add_space_permissions(space_key="MYSPACE", subject="john.doe", operation="read")
```

---

### 错误处理

```python
from atlassian.errors import ApiError

try:
    result = jira.issue("PROJ-999")
except ApiError as e:
    print(f"API error {e.status_code}: {e.reason}")
except Exception as e:
    print(f"Error: {e}")
```

---

### Windows 兼容性

- 使用 `python`（而非 `python3`），除非用户指定
- 路径使用 `os.path.join()` 或 `pathlib.Path`，勿硬编码斜杠
- 环境变量：CMD 用 `set VAR=value`，PowerShell 用 `$env:VAR = "value"`
- `os.environ.get()` 在所有平台行为一致

---

### 参考链接

- [atlassian-python-api 文档](https://atlassian-python-api.readthedocs.io/)
- [Jira REST API 参考](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Confluence REST API 参考](https://developer.atlassian.com/cloud/confluence/rest/v2/)
