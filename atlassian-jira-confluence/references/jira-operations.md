# Jira Operations Reference

Full method reference for `atlassian-python-api` Jira client. See SKILL.md for initialization patterns.

## Table of Contents
1. [Issue CRUD](#issue-crud)
2. [Search JQL](#search-jql)
3. [Comments](#comments)
4. [Attachments](#attachments)
5. [Transitions & Status](#transitions--status)
6. [Worklogs](#worklogs)
7. [Issue Links & Remote Links](#issue-links--remote-links)
8. [Issue Properties](#issue-properties)
9. [Watchers & Assignees](#watchers--assignees)
10. [Projects](#projects)
11. [Components](#components)
12. [Versions](#versions)
13. [Project Roles & Schemes](#project-roles--schemes)
14. [Custom Fields](#custom-fields)
15. [Issue Types / Priorities / Resolutions / Statuses](#issue-types--priorities--resolutions--statuses)
16. [Workflows & Screens](#workflows--screens)
17. [Dashboards & Filters](#dashboards--filters)
18. [Users & Groups](#users--groups)
19. [Agile: Boards, Sprints, Epics](#agile-boards-sprints-epics)
20. [Permissions](#permissions)
21. [Export](#export)
22. [Admin (Server/DC)](#admin-serverdc)
23. [Cluster Management (DC)](#cluster-management-dc)
24. [Tempo Plugin](#tempo-plugin)

---

## Issue CRUD

```python
# CREATE
issue = jira.issue_create(fields={
    "project": {"key": "PROJ"},
    "summary": "Short description",
    "description": "Detailed description",
    "issuetype": {"name": "Bug"},
    "priority": {"name": "High"},
    "labels": ["backend", "urgent"],
    "assignee": {"name": "username"},   # Server: name; Cloud: accountId
})
jira.create_issues([fields_1, fields_2])          # bulk create
jira.issue_create_or_update(fields)               # upsert

# READ
jira.issue("PROJ-1")
jira.issue("PROJ-1", fields="summary,status")     # selective fields
jira.issue_field_value("PROJ-1", "summary")
jira.issue_editmeta("PROJ-1")
jira.get_issue_changelog("PROJ-1")
jira.get_issue_status("PROJ-1")
jira.issue_exists("PROJ-1")
jira.issue_deleted("PROJ-1")

# UPDATE
jira.update_issue_field("PROJ-1", {"summary": "New summary"})
jira.issue_update(
    issue_key="PROJ-1",
    fields={"summary": "Updated", "priority": {"id": "2"}},
    update={"labels": [{"add": "triaged"}, {"remove": "old"}]},
    history_metadata={"activityDescription": "Updated via API"},
    notify_users=True,
)
jira.bulk_update_issue_field(["PROJ-1", "PROJ-2"], {"priority": {"name": "Low"}})
jira.issue_field_value_append("PROJ-1", "customfield_10000", {"name": "user"})

# DELETE
jira.delete_issue("PROJ-1")
jira.issue_archive("PROJ-1")    # Cloud only
jira.issue_restore("PROJ-1")   # Cloud only
```

---

## Search JQL

```python
# Basic
result = jira.jql("project = PROJ AND status = 'In Progress'", limit=50, fields="*all")
for issue in result.get("issues", []):
    print(issue["key"], issue["fields"]["summary"])

# Server: all pages
all_issues = jira.jql_get_list_of_tickets("project = PROJ")

# Cloud: token-based pagination (preferred)
for issue in jira.enhanced_jql("project = PROJ ORDER BY created DESC"):
    print(issue["key"])
all_issues = jira.enhanced_jql_get_list_of_tickets("project = PROJ")

# Check if issue matches JQL
jira.match_jql("PROJ-1", "priority >= High")

# Autocomplete
jira.get_autocomplete_data()
jira.get_autocomplete_suggestion("fixVersion", "1.0")

# Export
csv_data = jira.csv("project = PROJ", all_fields=False)
jira.excel("project = PROJ")
jira.export_html("project = PROJ")
```

---

## Comments

```python
# Read
jira.issue_get_comments("PROJ-1")
jira.issue_get_comment("PROJ-1", "comment-id")
jira.issues_get_comments_by_id("comment-id")

# Write
jira.issue_add_comment("PROJ-1", "Comment text")
jira.issue_edit_comment("PROJ-1", "comment-id", "Updated text",
                         visibility={"type": "role", "value": "Developers"})

# Properties
jira.get_comment_properties_keys("comment-id")
jira.set_comment_property("comment-id", "prop-key", {"value": "data"})
jira.delete_comment_property("comment-id", "prop-key")
```

---

## Attachments

```python
jira.add_attachment("PROJ-1", "/path/to/file.txt")
with open("file.txt", "rb") as f:
    jira.add_attachment_object("PROJ-1", f)

jira.get_attachments_ids_from_issue("PROJ-1")
jira.get_attachment_meta()
jira.download_attachments_from_issue("PROJ-1", path="./downloads/", cloud=True)
```

---

## Transitions & Status

```python
# List
jira.get_issue_transitions("PROJ-1")
jira.get_issue_transitions_full("PROJ-1")

# Transition by name
jira.issue_transition("PROJ-1", "In Progress")
jira.set_issue_status("PROJ-1", "Done")
jira.issue_transition("PROJ-1", "Done", fields={"resolution": {"name": "Fixed"}})

# Transition by ID
tid = jira.get_transition_id_to_status_name("PROJ-1", "Done")
jira.set_issue_status_by_transition_id("PROJ-1", tid)

# Query
jira.get_status_id_from_name("Done")
jira.get_issue_status_changelog("PROJ-1")
```

---

## Worklogs

```python
# Add — started format: "YYYY-MM-DDTHH:MM:SS.000+0000"
jira.issue_worklog("PROJ-1", started="2024-01-15T09:00:00.000+0000", time_in_sec=3600)

# Read
jira.issue_get_worklog("PROJ-1")
jira.get_updated_worklogs("2024-01-01")
jira.get_deleted_worklogs("2024-01-01")
jira.get_worklogs([worklog_id_1, worklog_id_2])
```

---

## Issue Links & Remote Links

```python
# Internal links
jira.create_issue_link({
    "type": {"name": "Duplicate"},
    "inwardIssue": {"key": "PROJ-1"},
    "outwardIssue": {"key": "PROJ-2"},
    "comment": {"body": "Linked!"},
})
jira.get_issue_link("link-id")
jira.remove_issue_link("link-id")

# Link types CRUD
jira.get_issue_link_types()
jira.create_issue_link_type({"name": "Relates", "inward": "relates to", "outward": "is related by"})
jira.get_issue_link_type("type-id")
jira.update_issue_link_type("type-id", {"name": "Blocks"})
jira.delete_issue_link_type("type-id")

# Remote links (to external URLs)
jira.create_or_update_issue_remote_links(
    "PROJ-1", "https://example.com", "External Docs",
    global_id="my-global-id", relationship="mentioned in",
)
jira.get_issue_remote_link_by_id("PROJ-1", "link-id")
jira.update_issue_remote_link_by_id("PROJ-1", "link-id", "https://new.url", "New Title")
jira.delete_issue_remote_link_by_id("PROJ-1", "link-id")
```

---

## Issue Properties

```python
jira.get_issue_property_keys("PROJ-1")
jira.get_issue_property("PROJ-1", "my-key")
jira.set_issue_property("PROJ-1", "my-key", {"data": "value"})
jira.delete_issue_property("PROJ-1", "my-key")
```

---

## Watchers & Assignees

```python
jira.issue_get_watchers("PROJ-1")
jira.issue_add_watcher("PROJ-1", "username")
jira.issue_delete_watcher("PROJ-1", "username")

jira.assign_issue("PROJ-1", account_id="user-account-id")   # Cloud
jira.assign_issue("PROJ-1", username="username")              # Server
jira.get_assignable_users_for_issue("PROJ-1")
jira.get_all_assignable_users_for_project("PROJ")
jira.get_users_with_browse_permission_to_a_project("username", project_key="PROJ")
```

---

## Projects

```python
# List / Read
jira.get_all_projects()
jira.project("PROJ")
jira.get_project_issues_count("PROJ")
jira.get_all_project_issues("PROJ", fields="*all", start=100, limit=500)
jira.get_project_issuekey_last("PROJ")
jira.get_project_issuekey_all("PROJ")
jira.get_all_project_types()
jira.get_all_project_categories()

# CRUD
jira.create_project_from_raw_json(project_json)
jira.update_project("PROJ", {"name": "New Name", "description": "Desc"})
jira.delete_project("PROJ")
jira.archive_project("PROJ")

# Permissions & Schemes
jira.get_project_permission_scheme("PROJ")
jira.assign_project_permission_scheme("PROJ", "scheme-id")
jira.get_project_notification_scheme("PROJ")
jira.assign_project_notification_scheme("PROJ", "scheme-id")
jira.get_project_issue_security_scheme("PROJ")
jira.get_priority_scheme_of_project("PROJ")
```

---

## Components

```python
jira.get_project_components("PROJ")
jira.component("component-id")
jira.create_component({"project": "PROJ", "name": "UI", "description": "Frontend component"})
jira.update_component({"id": "comp-id", "name": "Updated"}, "comp-id")
jira.delete_component("comp-id")
```

---

## Versions

```python
jira.get_project_versions("PROJ")
jira.get_project_versions_paginated("PROJ", start=0, limit=50, order_by="name")
jira.add_version("PROJ", "proj-id", "v1.0.0", is_archived=False, is_released=False)
jira.update_version("version-id", name="v1.0.1", is_released=True, release_date="2024-12-01")
jira.delete_version("version-id")
```

---

## Project Roles & Schemes

```python
jira.get_project_roles("PROJ")
jira.add_user_into_project_role("PROJ", "role-id", "username")
jira.delete_project_actors("PROJ", "role-id", "user")

jira.get_all_permissionschemes()
jira.create_permission_scheme(scheme_data)
jira.get_permission_scheme("scheme-id")
jira.set_permissionscheme_grant("scheme-id", grant_data)

jira.get_all_notification_schemes()
jira.get_all_issue_type_schemes()
jira.add_issue_type_scheme("PROJ", scheme_data)
```

---

## Custom Fields

```python
jira.get_all_fields()
jira.get_custom_fields(search="text", start=1, limit=50)
jira.get_custom_field_option("option-id")
jira.get_custom_field_options("field-id", "project-id")
jira.create_custom_field({
    "name": "My Field",
    "type": "com.atlassian.jira.plugin.system.customfieldtypes:text",
    "searcherKey": "com.atlassian.jira.plugin.system.customfieldtypes:textsearcher",
})
```

---

## Issue Types / Priorities / Resolutions / Statuses

```python
jira.get_issue_types()
jira.get_all_priorities()
jira.get_all_resolutions()
jira.get_all_statuses()
jira.get_status_for_project("PROJ")
jira.issue_createmeta_issuetypes("PROJ")
jira.issue_createmeta_fieldtypes("PROJ", "issuetype-id")
```

---

## Workflows & Screens

```python
jira.get_all_workflows()
jira.get_workflows_paginated(start=0, limit=50)
jira.get_all_screens()
jira.get_screen_tabs("screen-id")
```

---

## Dashboards & Filters

```python
# Dashboards
jira.get_dashboards()
jira.get_dashboard("dashboard-id")

# Filters
jira.create_filter("My Filter", "project = PROJ ORDER BY created DESC", favourite=True)
jira.get_filter("filter-id")
jira.edit_filter("filter-id", jql="project = PROJ2")
jira.delete_filter("filter-id")
jira.get_filter_share_permissions("filter-id")
jira.add_filter_share_permission("filter-id", "group", "jira-software-users")
jira.delete_filter_share_permission("filter-id", "permission-id")
```

---

## Users & Groups

```python
# Users
jira.myself()
jira.user("account-id")
jira.users_get_all()
jira.user_find_by_user_string("partial name")
jira.user_find_by_user_string(account_id="account-id")   # Cloud
jira.get_user_groups("account-id")                        # Cloud only
jira.user_create(email="u@e.com", username="u", name="User Name")
jira.user_update("account-id", {"displayName": "New Name"})
jira.user_remove("account-id")
jira.user_deactivate("account-id")   # 8.3.0+
jira.is_active_user("account-id")

# User properties
jira.user_properties("account-id")
jira.user_property("account-id", "key")
jira.user_set_property("account-id", "key", {"value": "data"})
jira.user_delete_property("account-id", "key")

# Groups
jira.get_groups(query="dev")
jira.create_group("my-group")
jira.remove_group("my-group", swap_group=None)
jira.get_all_users_from_group("my-group", include_inactive_users=False, start=0, limit=50)
jira.add_user_to_group(username="user", group_name="my-group")
jira.remove_user_from_group(username="user", group_name="my-group")

# Application roles (Cloud)
jira.get_all_application_roles()
jira.get_application_role("software")
jira.add_user_to_application("user")
jira.is_user_in_application("user")
```

---

## Agile: Boards, Sprints, Epics

```python
# Boards
jira.get_all_agile_boards(board_name=None, project_key="PROJ", board_type="scrum")
jira.get_agile_board("board-id")
jira.get_agile_board_configuration("board-id")
jira.create_agile_board(name="My Board", type="scrum", filter_id="filter-id")
jira.delete_agile_board("board-id")
jira.get_agile_board_by_filter_id("filter-id")
jira.get_issues_for_board("board-id", jql="", fields="*all", start=0, limit=50)

# Board properties
jira.get_agile_board_properties("board-id")
jira.get_agile_board_property("board-id", "key")
jira.set_agile_board_property("board-id", "key")
jira.delete_agile_board_property("board-id", "key")

# Velocity
jira.get_agile_board_refined_velocity("board-id")
jira.set_agile_board_refined_velocity("board-id", velocity_data)

# Sprints
jira.get_all_sprints_from_board("board-id", state=None)   # state: active|future|closed
jira.get_sprint("sprint-id")
jira.create_sprint("Sprint 1", origin_board_id="board-id",
                   start_datetime="2024-01-01T00:00:00.000Z",
                   end_datetime="2024-01-14T00:00:00.000Z", goal="Sprint goal")
jira.rename_sprint("sprint-id", "Sprint 2", start_date="...", end_date="...")
jira.delete_sprint("sprint-id")
jira.get_all_issues_for_sprint_in_board("board-id", state="active")
jira.add_issues_to_sprint("sprint-id", ["PROJ-1", "PROJ-2"])
jira.move_issues_to_backlog(["PROJ-3"])
jira.add_issues_to_backlog(["PROJ-4"])
jira.get_all_versions_from_board("board-id", released="true")

# Epics
jira.get_epics("board-id", done=False, start=0, limit=50)
jira.epic_issues("PROJ-100")
jira.get_issues_for_epic("board-id", "epic-id", jql="", fields="*all")
jira.get_issues_without_epic("board-id")
```

---

## Permissions

```python
jira.get_permissions("BROWSE_PROJECTS,EDIT_ISSUES")
jira.get_all_permissions()
jira.permissions(permissions, project_id=None, project_key="PROJ", issue_key="PROJ-1")
```

---

## Export

```python
jira.csv("project = PROJ", all_fields=False)
jira.excel("project = PROJ")
jira.export_html("project = PROJ")
```

---

## Admin (Server/DC)

```python
# System info
jira.get_server_info()
jira.get_configurations_of_jira()
jira.health_check()
jira.get_advanced_settings()
jira.get_property(key=None)
jira.set_property("property-id", "value")

# Reindexing
jira.reindex()
jira.reindex_project("PROJ")
jira.reindex_issue("PROJ-1")
jira.reindex_status()
jira.reindex_with_type(indexing_type="BACKGROUND_PREFERRED")
jira.index_checker()

# Plugins
jira.get_plugins_info()
jira.upload_plugin("/path/to/plugin.jar")
jira.delete_plugin("plugin-key")
jira.enable_plugin("plugin-key")
jira.disable_plugin("plugin-key")

# Audit logging
jira.get_audit_records(start=0, limit=10)
jira.post_audit_record(audit_record_data)

# Issue security schemes
jira.get_issue_security_schemes()
jira.get_issue_security_scheme("scheme-id", only_levels=False)
jira.get_all_issue_security_schemes()
```

---

## Cluster Management (DC)

```python
jira.get_cluster_all_nodes()
jira.get_cluster_alive_nodes()
jira.set_node_to_offline("node-id")
jira.delete_cluster_node("node-id")
jira.request_current_index_from_node("node-id")
jira.generate_support_zip_on_nodes(["node-1", "node-2"])
jira.check_support_zip_status("task-id")
jira.start_cluster_zdu_upgrade()
jira.get_cluster_zdu_state()
```

---

## Tempo Plugin

```python
# Search worklogs
jira.tempo_4_timesheets_find_worklogs(
    date_from="2024-01-01",
    date_to="2024-01-31",
    worker=["username"],
    projectKey=["PROJ"],
    includeSubtasks=True,
    maxResults=100,
)

# Accounts & Teams
jira.tempo_account_get_accounts()
jira.tempo_account_add_account(account_data)
jira.tempo_teams_get_all_teams()
jira.tempo_teams_add_member(team_id, member_data)

# Timesheets
jira.tempo_timesheets_get_worklogs()
jira.tempo_timesheets_write_worklog(worklog_data)
jira.tempo_timesheets_get_configuration()
jira.tempo_timesheets_get_team_utilization(team_id)

# Holiday & workload schemes
jira.tempo_holiday_get_schemes()
jira.tempo_workload_scheme_get_members(scheme_id)
```
