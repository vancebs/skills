# agent-code-review

自动化 Code Review Skill。Cron job 每分钟运行一次，监听 Gerrit 新提交，由 LLM 按 T2Mobile 编码规范审查，生成中文报告，并（正式模式下）发布到 Gerrit。

## 依赖

| Skill | 安装 | 用途 |
|---|---|---|
| T2MCodingRule | `npx skills add https://github.com/vancebs/skills --skill T2MCodingRule` | T2Mobile 编码规范知识库 |

## 快速开始

```bash
# 1. 检查环境（首次）
python3 "$SKILL_DIR/scripts/check_env.py"

# 2. 创建配置文件
mkdir -p "$SKILL_WORKSPACE/config/agent-code-review"
cp "$SKILL_DIR/scripts/config.json.example" \
   "$SKILL_WORKSPACE/config/agent-code-review/code_review_config.json"
# 编辑配置文件填入 Gerrit 凭据

# 3. 配置 cron job（每分钟）调用 review_job.py
# 详见 SKILL.md Step 3
```

## 脚本

| 脚本 | 说明 |
|---|---|
| `check_env.py` | 环境 & 依赖检查（加载 skill 后运行一次） |
| `review_job.py` | 主任务：监听进程管理 + 读取事件 + 拉取 diff |
| `post_result.py` | 提交 review 结果到 Gerrit |
| `config.json.example` | 配置模板 |

详细说明见 [SKILL.md](SKILL.md)。
