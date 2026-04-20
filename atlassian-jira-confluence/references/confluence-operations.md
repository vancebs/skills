# Confluence Operations Reference

Full method reference for `atlassian-python-api` Confluence client. See SKILL.md for initialization patterns.

## Table of Contents
1. [Initialization](#initialization)
2. [Pages: Read](#pages-read)
3. [Pages: Write](#pages-write)
4. [Spaces](#spaces)
5. [Attachments](#attachments)
6. [Labels](#labels)
7. [Comments](#comments)
8. [Templates](#templates)
9. [Whiteboards (Cloud)](#whiteboards-cloud)
10. [Users & Groups](#users--groups)
11. [Space Permissions](#space-permissions)
12. [Search (CQL)](#search-cql)
13. [Page Properties](#page-properties)
14. [Utilities & Admin](#utilities--admin)

---

## Initialization

```python
import os
from atlassian import Confluence

url   = os.environ["CONFLUENCE_URL"]
token = os.environ["CONFLUENCE_PAT_TOKEN"]

# PAT — Server / Data Center
confluence = Confluence(url=url, token=token)

# Cloud — use email + API token
confluence = Confluence(
    url=url,
    username=os.environ.get("CONFLUENCE_USERNAME", ""),
    password=token,
    cloud=True,
)
```

---

## Pages: Read

```python
# Check existence
confluence.page_exists("SPACE", "Page Title")
confluence.get_page_id("SPACE", "Page Title")

# Get page by title or ID
confluence.get_page_by_title("SPACE", "Page Title")
confluence.get_page_by_id(page_id, expand="body.storage,version,space")
confluence.get_draft_page_by_id(page_id, status="draft")

# Children / descendants / ancestors
confluence.get_page_child_by_type(page_id, type="page", start=None, limit=None)
confluence.get_page_ancestors(page_id)

# All pages in a space
confluence.get_all_pages_from_space("SPACE", start=0, limit=100,
                                    status=None, expand=None, content_type="page")
# Generator version (memory-efficient for large spaces)
for page in confluence.get_all_pages_from_space_as_generator("SPACE"):
    print(page["id"], page["title"])

# Trash & drafts
confluence.get_all_pages_from_space_trash("SPACE")
confluence.get_all_draft_pages_from_space("SPACE")
confluence.get_all_draft_pages_from_space_through_cql("SPACE")

# By label
confluence.get_all_pages_by_label("my-label", start=0, limit=50)

# Page history & versions
confluence.history(page_id)
confluence.get_content_history_by_version_number(page_id, version_number)

# Space content
confluence.get_space_content("SPACE", depth="all", start=0, limit=500,
                              content_type=None, expand="body.storage")
```

---

## Pages: Write

```python
# Create
result = confluence.create_page(
    space="SPACE",
    title="My New Page",
    body="<p>Page content in storage format (HTML).</p>",
    parent_id=None,       # optional parent page ID
    type="page",          # "page" or "blogpost"
    representation="storage",
    editor="v2",
    full_width=False,
)
page_id = result["id"]

# Update (increments version automatically)
confluence.update_page(
    page_id=page_id,
    title="Updated Title",
    body="<p>New content.</p>",
    parent_id=None,
    type="page",
    representation="storage",
    minor_edit=False,
    full_width=False,
)

# Update or create (upsert)
confluence.update_or_create(
    parent_id=parent_id,
    title="Page Title",
    body="<p>Content</p>",
    representation="storage",
)

# Append to existing page
confluence.append_page(
    page_id=page_id,
    title="Existing Title",
    append_body="<p>Appended section.</p>",
    minor_edit=True,
)

# Move page
confluence.move_page("SPACE", page_id, "Target Page Title", position="append")

# Delete
confluence.remove_page(page_id, status=None, recursive=False)  # recursive=True removes children too
confluence.remove_content(content_id)
confluence.remove_page_from_trash(page_id)
confluence.remove_page_as_draft(page_id)
confluence.remove_content_history(page_id, version_number)     # delete a specific version

# Convert wiki markup to storage format
confluence.convert_wiki_to_storage(wiki_text)

# Check if page already has the same content (avoid unnecessary updates)
confluence.is_page_content_is_already_updated(page_id, new_body)
```

---

## Spaces

```python
# List all spaces
confluence.get_all_spaces(start=0, limit=500, expand=None)

# Get a specific space
confluence.get_space("SPACE", expand="description.plain,homepage")

# Space content
confluence.get_space_content("SPACE", depth="all")

# Permissions
confluence.get_space_permissions("SPACE")        # JSON-RPC style
confluence.get_all_space_permissions("SPACE")    # REST API style

# Export
export_type = "TYPE_DOC"   # or "TYPE_PDF", "TYPE_HTML", "TYPE_XML"
confluence.get_space_export("SPACE", export_type)

# Archive
confluence.archive_space("SPACE")

# Trash
confluence.get_trashed_contents_by_space("SPACE", cursor=None, limit=100)
confluence.remove_trashed_contents_by_space("SPACE")
```

---

## Attachments

```python
# Upload file from path
confluence.attach_file(
    filename="/path/to/report.pdf",
    name="report.pdf",          # optional custom name
    content_type="application/pdf",
    page_id=page_id,            # OR: title="Page Title", space="SPACE"
    comment="Quarterly report",
)

# Upload in-memory content
confluence.attach_content(
    content=b"file bytes here",
    name="data.csv",
    content_type="text/csv",
    page_id=page_id,
)

# List attachments on a page
confluence.get_attachments_from_content(page_id, start=0, limit=50,
                                         filename=None, media_type=None)

# Download all attachments from page to local directory
confluence.download_attachments_from_page(page_id, path="./downloads/")

# Delete
confluence.delete_attachment(page_id, filename)
confluence.delete_attachment_by_id(attachment_id, version)
confluence.remove_page_attachment_keep_version(page_id, filename, keep_last_versions=3)

# Attachment history
confluence.get_attachment_history(attachment_id, limit=200, start=0)

# Check for broken attachments
confluence.has_unknown_attachment_error(page_id)
```

---

## Labels

```python
# Add labels to a page
confluence.set_page_label(page_id, "my-label")

# Remove a label
confluence.remove_page_label(page_id, "my-label")

# Get labels on a page
confluence.get_page_labels(page_id, prefix=None, start=None, limit=None)

# Find all pages with a label
confluence.get_all_pages_by_label("my-label", start=0, limit=50)
```

---

## Comments

```python
# Add comment (storage format body)
confluence.add_comment(page_id, "<p>This is a comment.</p>")

# Inline task checkbox
confluence.set_inline_tasks_checkbox(page_id, task_id, status="complete")
```

---

## Templates

```python
# List templates
confluence.get_content_templates()               # global
confluence.get_content_templates("SPACE")        # space-specific
confluence.get_blueprint_templates()             # global blueprints
confluence.get_blueprint_templates("SPACE")      # space blueprints

# Get one template
confluence.get_content_template(template_id)

# Create / update
confluence.create_or_update_template(
    name="My Template",
    body={"value": "<p>Template body</p>", "representation": "storage"},
    template_type="page",
    template_id=None,            # omit to create new
    description="Used for X",
    labels=[{"name": "tmpl"}],
    space="SPACE",
)

# Delete
confluence.remove_template(template_id)
```

---

## Whiteboards (Cloud)

```python
# Create
confluence.create_whiteboard(spaceId="space-id", title="My Whiteboard", parentId=None)

# Read
confluence.get_whiteboard(whiteboard_id)

# Delete
confluence.delete_whiteboard(whiteboard_id)
```

---

## Users & Groups

```python
# User lookup
confluence.get_user_details_by_username("username", expand=None)
confluence.get_user_details_by_userkey("user-key", expand=None)

# Change passwords
confluence.change_user_password("username", "newpass")
confluence.change_my_password("oldpass", "newpass")

# Groups
confluence.get_all_groups(start=0, limit=1000)

# Group membership
confluence.add_user_to_group("username", "group-name")
confluence.remove_user_from_group("username", "group-name")
```

---

## Space Permissions

```python
# Get current permissions
confluence.get_all_space_permissions("SPACE")

# Anonymous permissions
confluence.get_permissions_granted_to_anonymous_for_space("SPACE")
confluence.set_permissions_to_anonymous_for_space("SPACE", operations=[
    {"targetType": "space", "operationKey": "read"},
    {"targetType": "page",  "operationKey": "create"},
])
confluence.remove_permissions_granted_to_anonymous_for_space("SPACE")

# Group permissions
confluence.get_permissions_granted_to_group_for_space("SPACE", "group-name")
confluence.set_permissions_to_group_for_space("SPACE", "group-name", operations=[
    {"targetType": "space", "operationKey": "read"},
])
confluence.remove_permissions_from_group_for_space("SPACE", "group-name")

# User permissions
confluence.get_permissions_granted_to_user_for_space("SPACE", "user-key")
confluence.set_permissions_to_user_for_space("SPACE", "user-key", operations=[
    {"targetType": "space", "operationKey": "read"},
])
confluence.remove_permissions_from_user_for_space("SPACE", "user-key")

# Bulk set
confluence.set_permissions_to_multiple_items_for_space(
    "SPACE",
    user_key="user-key",
    group_name="group-name",
    operations=[{"targetType": "page", "operationKey": "create"}],
)

# Legacy JSON-RPC permission helpers
confluence.add_space_permissions("SPACE", user_key, group_name, operations)
confluence.remove_space_permissions("SPACE", user_key, group_name, permission)
```

---

## Search (CQL)

CQL (Confluence Query Language) works like SQL for Confluence content.

```python
# Full text + filtered search
results = confluence.cql(
    cql='space = "SPACE" AND type = page AND text ~ "deployment"',
    start=0,
    limit=20,
    expand=None,
    include_archived_spaces=False,
    excerpt=None,
)
for item in results.get("results", []):
    print(item["title"], item["_links"]["webui"])

# Useful CQL examples:
# All pages in a space modified in the last 7 days:
#   space = "SPACE" AND type = page AND lastModified > now("-7d")
# Pages with a specific label:
#   type = page AND label = "release-notes"
# Full-text across all spaces:
#   text ~ "API gateway" AND type = page
# Blog posts by a user:
#   type = blogpost AND creator = "username"
```

---

## Page Properties

```python
# Set key-value metadata on a page (useful for custom data, integrations)
confluence.set_page_property(page_id, {
    "key": "my-property",
    "value": {"status": "reviewed", "reviewer": "jdoe"},
    "version": {"number": 1, "minorEdit": True},
})

# Read
confluence.get_page_property(page_id, "my-property")
confluence.get_page_properties(page_id)

# Delete
confluence.delete_page_property(page_id, "my-property")

# Restrictions
confluence.get_all_restrictions_for_content(page_id)
```

---

## Utilities & Admin

```python
# Export page as PDF
# set api_version="cloud" for Confluence Cloud
pdf_bytes = confluence.export_page(page_id)
with open("page.pdf", "wb") as f:
    f.write(pdf_bytes)

# Extract tables from a page (returns list of 2D lists)
tables = confluence.get_tables_from_page(page_id)

# Regex scraping from a page
matches = confluence.scrap_regex_from_page(page_id, r"PROJ-\d+")

# Cache management (Server)
confluence.clean_all_caches()
confluence.clean_package_cache("com.gliffy.cache.gon")

# Reindex (Server)
confluence.reindex()
```
