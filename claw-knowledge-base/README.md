# claw-knowledge-base

> ⚠️ **OpenClaw 平台专用 skill**

OpenClaw 多 Agent 共享知识库。`KNOWLEDGE_BASE_DIR` 下所有 `.md` 文件自动被 OpenClaw 索引，所有 Agent 均可通过 `memory_search` 检索。

## 快速开始

```bash
# 1. 设置环境变量
export KNOWLEDGE_BASE_DIR="/path/to/your/knowledge-base"

# 2. 检查环境
python3 scripts/check_env.py

# 3. 初始化目录结构（一次性）
python3 scripts/init_dirs.py

# 4. 配置 openclaw.json（见 SKILL.md Step 3）
```

## 目录结构

```
knowledge-base/
├── architecture/       # 系统架构文档
├── coding-standards/   # 编码规范
├── troubleshooting/    # 问题解决方案
├── release-notes/      # 版本记录
├── code-review/        # CR 记录
├── temp/               # 临时文件（定期清理）
├── onboarding/         # 入职指南
└── {agent_def_dir}/    # Agent 私有目录
```

详细使用说明见 [SKILL.md](SKILL.md)。
