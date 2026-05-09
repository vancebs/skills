skill|install|comment
-|-|-
atlassian-jira-confluence|npx skills add https://github.com/vancebs/skills --skill atlassian-jira-confluence|jira & confluence skill
T2MCodingRule|npx skills add https://github.com/vancebs/skills --skill T2MCodingRule|T2Mobile编码规范与开发流程知识库
gerrit-api|npx skills add https://github.com/vancebs/skills --skill gerrit-api|Gerrit Code Review REST API 与 SSH 事件流

## Skill 清单

| Skill | 功能简述 | 详细说明 |
|---|---|---|
| [gerrit-api](gerrit-api/) | 通过 REST API 与 Gerrit Code Review 交互（查询变更、发布审查、管理生命周期），并通过 SSH 实时监听 Gerrit 事件流。纯 Python 实现，跨平台兼容 Windows / Linux / macOS。 | [📖 README](gerrit-api/README.md) |
| [atlassian-jira-confluence](atlassian-jira-confluence/) | 通过 `atlassian-python-api` SDK 与 Jira 和 Confluence 进行全功能交互，支持 Issue 管理、看板 & Sprint、页面管理、CQL 搜索、附件、权限等所有 SDK 覆盖操作。兼容 Cloud 和 Data Center。 | [📖 README](atlassian-jira-confluence/README.md) |
| [T2MCodingRule](T2MCodingRule/) | T2Mobile 公司编码规范与开发流程知识库，涵盖 Git Commit Message 规范、Code Review 流程、Java / C / C++ 编码规范、安全规范、兼容性规范。纯知识库，无需配置。 | [📖 README](T2MCodingRule/README.md) |
