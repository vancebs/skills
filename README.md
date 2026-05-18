## Skill 清单

| Skill | 功能简述 | 详细说明 | 安装 |
|---|---|---|---|
| [gerrit-api](gerrit-api/) | 通过 REST API 与 Gerrit Code Review 交互（查询变更、发布审查、管理生命周期），并通过 SSH 实时监听 Gerrit 事件流。纯 Python 实现，跨平台兼容 Windows / Linux / macOS。 | [📖 README](gerrit-api/README.md) | `npx skills add https://github.com/vancebs/skills --skill gerrit-api` |
| [atlassian-jira-confluence](atlassian-jira-confluence/) | 通过 `atlassian-python-api` SDK 与 Jira 和 Confluence 进行全功能交互，支持 Issue 管理、看板 & Sprint、页面管理、CQL 搜索、附件、权限等所有 SDK 覆盖操作。兼容 Cloud 和 Data Center。 | [📖 README](atlassian-jira-confluence/README.md) | `npx skills add https://github.com/vancebs/skills --skill atlassian-jira-confluence` |
| [T2MCodingRule](T2MCodingRule/) | T2Mobile 公司编码规范与开发流程知识库，涵盖 Git Commit Message 规范、Code Review 流程、Java / C / C++ 编码规范、安全规范、兼容性规范。纯知识库，无需配置。 | [📖 README](T2MCodingRule/README.md) | `npx skills add https://github.com/vancebs/skills --skill T2MCodingRule` |
| [agent-code-review](agent-code-review/) | 自动化 Code Review。持续监听 Gerrit 事件流，对新提交按 T2Mobile 编码规范进行审查，生成中文 PASS/FAIL 报告，并（非测试模式下）发布 Gerrit comment 并设置 Verified 标签。依赖 gerrit-api 和 T2MCodingRule。 | [📖 README](agent-code-review/README.md) | `npx skills add https://github.com/vancebs/skills --skill agent-code-review` |
| [code-review](code-review/) | 按需 Code Review。当 agent 收到 Gerrit 变更信息（页面 URL、change-id、commit SHA 或 stream event JSON）时，拉取 patch 并进行代码审查，生成报告并可发布到 Gerrit。无需事件监听或 cron job，专注单次审查任务。 | [📖 README](code-review/README.md) | `npx skills add https://github.com/vancebs/skills --skill code-review` |
| [claw-knowledge-base](claw-knowledge-base/) | OpenClaw 平台多 Agent 共享知识库。管理 `KNOWLEDGE_BASE_DIR` 下分类 Markdown 文件，所有 `.md` 文件自动被 OpenClaw 索引，Agent 可通过 `memory_search` 语义检索，并按目录规范存入知识。仅支持 OpenClaw 平台。 | [📖 README](claw-knowledge-base/README.md) | `npx skills add https://github.com/vancebs/skills --skill claw-knowledge-base` |
| [t2-config](t2-config/) | 集中管理 agent skills 配置。使用 `cfg://<namespace>/<key>` 协议读写 `${CFG_DIR}/<namespace>.json`，为 gerrit-api、atlassian、code-review 等 skill 提供统一的凭据存储，避免重复配置。纯 Python 实现，无需 pip。 | [📖 README](t2-config/README.md) | `npx skills add https://github.com/vancebs/skills --skill t2-config` |
