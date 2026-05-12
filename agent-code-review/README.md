# agent-code-review

自动化 Code Review Skill。Agent 监听 Gerrit 事件流，对每个新提交按 T2Mobile 编码规范进行审查，生成中文 PASS/FAIL 报告，并（非测试模式下）发布到 Gerrit。

## 依赖

| Skill | 安装 | 用途 |
|---|---|---|
| gerrit-api | `npx skills add https://github.com/vancebs/skills --skill gerrit-api` | 访问 Gerrit REST API / SSH 事件流 |
| T2MCodingRule | `npx skills add https://github.com/vancebs/skills --skill T2MCodingRule` | T2Mobile 编码规范知识库 |

## 功能

- 持续监听 `patchset-created` 事件（通过 `gerrit_stream_events.py`）
- 每分钟自动读取事件队列（原子操作，无竞态）
- 对每个 patchset 的所有修改文件进行 code review：
  - Java/C/C++ 文件按 T2MCodingRule 审查
  - 其他语言按通用代码质量标准（只警告不 FAIL）
- 生成结构化中文报告（PASS/FAIL + 问题列表 + 修改建议）
- **测试模式**（默认开启）：报告仅输出到会话，不写 Gerrit
- **正式模式**：自动发布 Gerrit comment，FAIL 时设置 Verified=-1

## 配置

```bash
# 1. 创建配置目录
mkdir -p config/agent-code-review

# 2. 复制模板
cp scripts/agent_code_review_config.json.example \
   config/agent-code-review/agent_code_review_config.json

# 3. 编辑配置（至少设置 test_mode 和 events_file）
```

主要配置项：
- `test_mode: true` — 默认开启，仅输出报告到会话
- `events_file` — 事件队列文件路径（默认 `{workspace}/events.jsonl`）

详细说明见 [SKILL.md](SKILL.md)。

## 快速开始

```bash
# 1. 设置 workspace
export SKILL_WORKSPACE="$(pwd)"

# 2. 启动事件流监听
python3 "$SKILL_WORKSPACE/scripts/gerrit_stream_events.py" \
  --output "$SKILL_WORKSPACE/events.jsonl" \
  --filter patchset-created --reconnect --quiet &

# 3. 手动触发一次 code review（测试用）
python3 "$SKILL_WORKSPACE/scripts/poll_events.py" \
  --workspace "$SKILL_WORKSPACE" --dry-run
```
