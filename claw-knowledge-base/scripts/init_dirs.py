#!/usr/bin/env python3
"""
init_dirs.py — claw-knowledge-base directory initializer
Creates standard subdirectories under KNOWLEDGE_BASE_DIR.
IDEMPOTENT: existing directories and files are never overwritten.

Exit codes:
  0 = success (all dirs created or already exist)
  1 = fatal error (KNOWLEDGE_BASE_DIR not set, not absolute, not writable)
"""

import os
import sys
from pathlib import Path

DIRS_WITH_DESC = {
    "architecture": "系统架构文档（层级、模块划分、关键设计决策）",
    "coding-standards": "编码规范和最佳实践",
    "troubleshooting": "常见问题和解决方案",
    "release-notes": "版本发布记录",
    "code-review": "Code Review 记录和重要决策",
    "temp": "Agent 之间临时文件分享（读取后请删除）",
    "onboarding": "新成员入职指南、环境搭建说明",
}

README_TEMPLATE = """\
# {title}

{desc}

## 文件命名规范

- 使用小写英文 + 连字符，格式：`[a-z0-9][a-z0-9-]*.md`
- 示例：`example-document.md`

## 内容要求

- 文件第一行必须为 `# 标题`
- 包含足够的关键词便于 `memory_search` 语义检索
- 代码片段使用 fenced code block
- 单文件大小 ≤ 1 MB
"""

TEMP_README = """\
# temp — 临时文件目录

此目录用于 Agent 之间一次性文件传递。

## 使用规则

- **写入时** 在文件头注明过期时间：`expires: YYYY-MM-DD`
- **读取后** 由读取方负责删除该文件
- **禁止** 在此目录存放长期有效的知识文档

## 文件命名示例

`agent-a-to-b-2026-05-18.md`
"""


def fatal(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)


# ── Validate KNOWLEDGE_BASE_DIR ────────────────────────────────────────────────
kb_raw = os.environ.get("KNOWLEDGE_BASE_DIR", "")
if not kb_raw:
    fatal("KNOWLEDGE_BASE_DIR 未设置。\n"
          "   请先设置: export KNOWLEDGE_BASE_DIR=\"/abs/path/to/knowledge-base\"\n"
          "   或在 openclaw.json 的 env 字段中配置。")

if not os.path.isabs(kb_raw):
    fatal(f"KNOWLEDGE_BASE_DIR 必须为绝对路径，当前值: {kb_raw!r}")

kb = Path(kb_raw)

# ── Create root directory if needed ───────────────────────────────────────────
if not kb.exists():
    try:
        kb.mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建根目录: {kb}")
    except OSError as e:
        fatal(f"无法创建目录 {kb}: {e}")
elif not kb.is_dir():
    fatal(f"{kb} 已存在但不是目录")

if not os.access(kb, os.W_OK):
    fatal(f"目录 {kb} 不可写。请检查权限。")

# ── Create subdirectories ──────────────────────────────────────────────────────
created = []
skipped = []

for dirname, desc in DIRS_WITH_DESC.items():
    subdir = kb / dirname
    if not subdir.exists():
        subdir.mkdir()
        created.append(dirname)
        print(f"✅ 创建子目录: {dirname}/")
    else:
        skipped.append(dirname)
        print(f"   已存在（跳过）: {dirname}/")

    # Write README.md if not present
    readme = subdir / "README.md"
    if not readme.exists():
        if dirname == "temp":
            content = TEMP_README
        else:
            title = dirname.replace("-", " ").title()
            content = README_TEMPLATE.format(title=title, desc=desc)
        readme.write_text(content, encoding="utf-8")
        print(f"   ✅ 写入 {dirname}/README.md")

# ── Summary ───────────────────────────────────────────────────────────────────
print()
if created:
    print(f"✅ 新创建 {len(created)} 个子目录: {', '.join(created)}")
if skipped:
    print(f"   已存在（未修改）: {len(skipped)} 个: {', '.join(skipped)}")
print(f"\n知识库根目录: {kb}")
print("初始化完成。下一步请确认 openclaw.json 已配置 memorySearch.extraPaths（见 SKILL.md Step 3）。")
sys.exit(0)
