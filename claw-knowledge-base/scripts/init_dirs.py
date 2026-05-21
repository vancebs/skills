#!/usr/bin/env python3
"""
init_dirs.py — claw-knowledge-base directory initializer
Creates standard subdirectories under KNOWLEDGE_BASE_DIR.
IDEMPOTENT: existing directories and files are never overwritten.

Exit codes:
  0 = success (all dirs created or already exist)
  1 = fatal error (KNOWLEDGE_BASE_DIR not set, not absolute, not writable)
"""

import argparse
import json
import os
import sys
from pathlib import Path

DIRS_WITH_DESC = {
    "architecture": "系统架构文档（层级、模块划分、关键设计决策）",
    "coding-standards": "编码规范和最佳实践",
    "troubleshooting": "常见问题和解决方案",
    "release-notes": "版本发布记录",
    "code-review": "存档 code review 报告（每次审查生成一份，命名格式 YYYY-MM-DD_<change>.md）",
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

CODE_REVIEW_README = """\
# code-review — Code Review 报告归档

此目录用于存档每次 code review 的完整报告。

## 文件命名格式

`YYYY-MM-DD_<change>.md`，其中 `<change>` 为 Gerrit change number。

示例：`2026-05-18_12345.md`

## 使用规则

- 每次 code review 完成后，将完整报告以上述命名格式写入本目录
- 报告内容包含：变更信息、审查结果（PASS/FAIL）、问题列表
- 文件第一行必须为 `# 标题`（H1）
- 不得在此目录存放非 code review 相关文档
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


def _load_file_config(workspace: str | None = None) -> dict:
    """Load .config/claw-knowledge-base.json from workspace or home."""
    candidates = []
    if workspace:
        candidates.append(Path(workspace) / ".config" / "claw-knowledge-base.json")
    candidates.append(Path.cwd() / ".config" / "claw-knowledge-base.json")
    candidates.append(Path.home() / ".config" / "claw-knowledge-base.json")
    seen, search = set(), []
    for p in candidates:
        k = str(p)
        if k not in seen:
            seen.add(k)
            search.append(p)
    for path in search:
        if path.is_file():
            try:
                d = json.loads(path.read_text(encoding="utf-8"))
                return d if isinstance(d, dict) else {}
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def fatal(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", help="Workspace path for config lookup")
    args = parser.parse_args()

    cfg = _load_file_config(args.workspace)
    kb_raw = (cfg.get("KNOWLEDGE_BASE_DIR") or os.environ.get("KNOWLEDGE_BASE_DIR", "")).strip()
    if not kb_raw:
        fatal("KNOWLEDGE_BASE_DIR 未设置。\n"
              "   Option 1: 在 .config/claw-knowledge-base.json 中添加 {\"KNOWLEDGE_BASE_DIR\": \"/abs/path\"}\n"
              "   Option 2: 在 openclaw.json 的 env 字段中添加: \"KNOWLEDGE_BASE_DIR\": \"/abs/path/to/knowledge-base\"")

    if not os.path.isabs(kb_raw):
        fatal(f"KNOWLEDGE_BASE_DIR 必须为绝对路径，当前值: {kb_raw!r}")

    kb = Path(kb_raw)

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

        readme = subdir / "README.md"
        if not readme.exists():
            if dirname == "temp":
                content = TEMP_README
            elif dirname == "code-review":
                content = CODE_REVIEW_README
            else:
                title = dirname.replace("-", " ").title()
                content = README_TEMPLATE.format(title=title, desc=desc)
            readme.write_text(content, encoding="utf-8")
            print(f"   ✅ 写入 {dirname}/README.md")

    print()
    if created:
        print(f"✅ 新创建 {len(created)} 个子目录: {', '.join(created)}")
    if skipped:
        print(f"   已存在（未修改）: {len(skipped)} 个: {', '.join(skipped)}")
    print(f"\n知识库根目录: {kb}")
    print("初始化完成。下一步请确认 openclaw.json 已配置 memorySearch.extraPaths（见 SKILL.md Step 3）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
