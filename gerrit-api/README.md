# gerrit-api

## 功能简述

通过 Gerrit REST API 和 SSH stream-events 与 Gerrit Code Review 系统交互。支持查询变更、读取差异、发布代码审查意见、管理变更生命周期，以及实时监听 Gerrit 事件流。纯 Python 实现，兼容 Windows、Linux 和 macOS。

---

## 配置

### 配置文件（推荐）

按以下优先级自动搜索配置文件：

| 优先级 | 路径 |
|---|---|
| 1（推荐） | `{workspace}/config/gerrit-api/gerrit_config.json` |
| 2 | `{workspace}/config/gerrit_config.json` |
| 3 | `{workspace}/gerrit_config.json` |
| 4 | `{skill-dir}/gerrit_config.json` |
| 5 | `$HOME/.config/gerrit-api/gerrit_config.json` |
| 6 | `$HOME/.config/gerrit_config.json` |
| 7 | `$HOME/gerrit_config.json` |

`{workspace}` 为运行脚本时的当前目录。建议将配置文件创建在最高优先级路径：

```bash
mkdir -p config/gerrit-api
cp /path/to/gerrit-api/scripts/gerrit_config.json.example config/gerrit-api/gerrit_config.json
```

配置文件格式（参考 `scripts/gerrit_config.json.example`）：

```json
{
  "url": "https://gerrit.example.com",
  "username": "john.doe",
  "password": "your-http-credential-token",

  "ssh_host": "gerrit.example.com",
  "ssh_port": 29418,
  "ssh_username": "john.doe",
  "ssh_key": "~/.ssh/id_rsa"
}
```

| 字段 | 说明 |
|---|---|
| `url` | Gerrit 实例 URL（无尾部斜杠） |
| `username` | Gerrit HTTP 用户名（Settings → Profile） |
| `password` | HTTP 凭据令牌（Settings → HTTP Credentials → Generate Password） |
| `ssh_host` | SSH 主机名（可从 `url` 自动推导） |
| `ssh_port` | SSH 端口，默认 `29418` |
| `ssh_username` | SSH 用户名，默认与 `username` 相同 |
| `ssh_key` | SSH 私钥路径，留空则使用 `~/.ssh/` 默认密钥 |

> **注意**：`password` 是 Gerrit 专用 HTTP 凭据令牌，不是登录密码。`ssh_*` 字段仅 stream-events 功能需要。

### 环境变量（回退）

配置文件缺失或对应字段为空时自动回退：

| 环境变量 | 对应字段 |
|---|---|
| `GERRIT_URL` | `url` |
| `GERRIT_USERNAME` | `username` |
| `GERRIT_HTTP_PASSWORD` | `password` |
| `GERRIT_SSH_HOST` | `ssh_host` |
| `GERRIT_SSH_PORT` | `ssh_port` |
| `GERRIT_SSH_USERNAME` | `ssh_username` |
| `GERRIT_SSH_KEY` | `ssh_key` |

---

## 详细功能描述

### REST API（`scripts/gerrit_api.py`）

跨平台 Python 脚本，封装 Gerrit REST API，无需额外依赖（仅用标准库）。

```bash
# 查询变更
python scripts/gerrit_api.py query "status:open+limit:5"
python scripts/gerrit_api.py query "status:open+owner:self" CURRENT_REVISION DETAILED_LABELS

# 获取变更详情
python scripts/gerrit_api.py get-change 12345
python scripts/gerrit_api.py get-change 12345 CURRENT_REVISION DETAILED_LABELS MESSAGES

# 列出变更涉及的文件
python scripts/gerrit_api.py list-files 12345
python scripts/gerrit_api.py list-files 12345 2          # 指定 patch set

# 查看文件差异
python scripts/gerrit_api.py get-diff 12345 "src/main/App.java"

# 获取文件原始内容（输出到 stdout）
python scripts/gerrit_api.py get-content 12345 "src/main/App.java"

# 发布代码审查（含标签和评论）
python scripts/gerrit_api.py review 12345 current \
  '{"message":"LGTM","labels":{"Code-Review":1}}'

python scripts/gerrit_api.py review 12345 current '{
  "message": "A few comments.",
  "labels": {"Code-Review": -1},
  "comments": {
    "src/main/App.java": [
      {"line": 23, "message": "Consider renaming.", "unresolved": true}
    ]
  }
}'

# 创建草稿评论
python scripts/gerrit_api.py create-draft 12345 current \
  '{"path":"src/main/App.java","line":23,"message":"[nit]","unresolved":true}'

# 提交变更
python scripts/gerrit_api.py submit 12345

# 放弃 / 恢复变更
python scripts/gerrit_api.py abandon 12345 "Superseded by #12346"
python scripts/gerrit_api.py restore 12345

# 添加 Reviewer
python scripts/gerrit_api.py add-reviewer 12345 jane.roe@example.com

# 设置 Topic
python scripts/gerrit_api.py set-topic 12345 my-feature
```

#### 支持的命令

| 命令 | 说明 |
|---|---|
| `query <query> [OPTION...]` | 查询变更列表（最多 25 条） |
| `get-change <id> [OPTION...]` | 获取变更详情 |
| `list-files <id> [revision]` | 列出变更文件 |
| `get-diff <id> <file> [revision]` | 获取文件 diff |
| `get-content <id> <file> [revision]` | 获取文件原始内容（base64 解码后输出） |
| `create-draft <id> <revision> <json>` | 创建草稿评论 |
| `review <id> <revision> <json>` | 发布审查（标签 + 评论） |
| `submit <id>` | 提交合入变更 |
| `abandon <id> [message]` | 放弃变更 |
| `restore <id> [message]` | 恢复已放弃的变更 |
| `add-reviewer <id> <account>` | 添加 Reviewer |
| `set-topic <id> <topic>` | 设置 Topic |
| `help` | 显示帮助 |

#### Gerrit 查询选项（`OPTION`）

常用 `o` 参数（可叠加）：

| 参数 | 含义 |
|---|---|
| `CURRENT_REVISION` | 包含当前 patch set 信息 |
| `DETAILED_LABELS` | 包含详细投票信息 |
| `DETAILED_ACCOUNTS` | 包含完整用户信息 |
| `CURRENT_FILES` | 包含当前 patch set 的文件列表 |
| `MESSAGES` | 包含变更消息历史 |

---

### SSH Stream Events（`scripts/gerrit_stream_events.py`）

通过 SSH 持续监听 Gerrit 事件流，将每个事件解析为结构化 JSON 输出到 stdout。

```bash
# 监听所有事件（Ctrl+C 停止）
python scripts/gerrit_stream_events.py

# 只监听新 patch set 上传和合入事件，格式化输出
python scripts/gerrit_stream_events.py \
  --filter patchset-created,change-merged --pretty

# 显示单行可读摘要
python scripts/gerrit_stream_events.py --summary

# 收集 20 个事件后退出（测试用）
python scripts/gerrit_stream_events.py --max-events 20

# 运行 5 分钟，写入日志文件，断线自动重连
python scripts/gerrit_stream_events.py \
  --timeout 300 --output events.jsonl --reconnect

# 过滤特定项目，管道给 jq 处理
python scripts/gerrit_stream_events.py \
  --filter patchset-created --project myOrg/myRepo \
  | jq '{type, change: .change.number, uploader: .uploader.name}'
```

#### 支持的事件类型

| 事件类型 | 触发时机 |
|---|---|
| `patchset-created` | 上传新 patch set |
| `change-merged` | 变更合入 |
| `change-abandoned` | 变更放弃 |
| `change-restored` | 变更恢复 |
| `comment-added` | 发布评论或投票 |
| `reviewer-added` | 添加 reviewer |
| `reviewer-deleted` | 移除 reviewer |
| `vote-deleted` | 删除投票 |
| `topic-changed` | 修改 topic |
| `hashtags-changed` | 修改 hashtag |
| `ref-updated` | git ref 变更（push/delete） |
| `project-created` | 新建项目 |

每个输出事件都附加了：
- `_received_at`：接收时间（UTC ISO 8601）
- `summary`：可读的单行摘要

#### Agent 使用模式

**模式 A：后台监听 + 读取日志文件**
```bash
# 后台启动（async bash）
python scripts/gerrit_stream_events.py --output events.jsonl --reconnect --quiet &

# 定期读取
tail -n 50 events.jsonl | python -c "
import sys, json
for line in sys.stdin:
    ev = json.loads(line)
    print(ev['type'], ev.get('change', {}).get('number', ''))
"
```

**模式 B：有界批量采集**
```bash
python scripts/gerrit_stream_events.py --timeout 30 --filter patchset-created \
  > batch.jsonl
# 然后统一处理 batch.jsonl
```

**模式 C：管道实时处理**
```bash
python scripts/gerrit_stream_events.py --filter patchset-created \
  | while IFS= read -r event; do
      CHANGE=$(echo "$event" | python -c "import sys,json; print(json.load(sys.stdin)['change']['number'])")
      python scripts/gerrit_api.py review "$CHANGE" current '{"message":"CI triggered"}'
    done
```

---

### 依赖

| 工具 | 用途 | 是否必须 |
|---|---|---|
| Python 3.9+ | 运行所有脚本 | ✅ 必须 |
| ssh | stream-events SSH 连接 | stream-events 需要 |

REST API 脚本（`gerrit_api.py`）仅使用 Python 标准库，无需安装额外包。

---

### 参考链接

- [Gerrit REST API 文档](https://gerrit-review.googlesource.com/Documentation/rest-api.html)
- [Gerrit Changes REST API](https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html)
- [Gerrit Stream Events（SSH）](https://gerrit-review.googlesource.com/Documentation/cmd-stream-events.html)
- [Gerrit 搜索语法](https://gerrit-review.googlesource.com/Documentation/user-search.html)
