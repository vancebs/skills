#!/usr/bin/env python3
"""
check_env.py — claw-knowledge-base environment checker
Verifies KNOWLEDGE_BASE_DIR, directory permissions, openclaw.json config,
and standard subdirectory existence.

Exit codes:
  0 = all checks passed
  1 = one or more checks failed (see output for details)
"""

import json
import os
import re
import sys
from pathlib import Path

REQUIRED_DIRS = [
    "architecture",
    "coding-standards",
    "troubleshooting",
    "release-notes",
    "code-review",
    "temp",
    "onboarding",
]

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

errors = []


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


def check(ok: bool, label: str, detail: str = "", fix: str = "") -> bool:
    icon = PASS if ok else FAIL
    line = f"{icon} {label}"
    if detail:
        line += f": {detail}"
    print(line)
    if not ok and fix:
        print(f"   → 解决方法: {fix}")
    if not ok:
        errors.append(label)
    return ok


# ── 1. Platform check ──────────────────────────────────────────────────────────
is_openclaw = os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("OPENCLAW_ENV")
if not is_openclaw:
    print(f"{WARN} 未检测到 OpenClaw 环境变量（OPENCLAW_WORKSPACE / OPENCLAW_ENV）")
    print("   本 skill 仅支持 OpenClaw 平台。若您在 OpenClaw 中运行，可忽略此提示。")

# ── 2. KNOWLEDGE_BASE_DIR set ──────────────────────────────────────────────────
cfg = _load_file_config()
kb_raw = (cfg.get("KNOWLEDGE_BASE_DIR") or os.environ.get("KNOWLEDGE_BASE_DIR", "")).strip()
if cfg:
    print(f"{WARN} 配置来源: 配置文件")
if not kb_raw:
    check(False, "KNOWLEDGE_BASE_DIR",
          "未设置",
          "Option 1: 在 .config/claw-knowledge-base.json 中添加 {\"KNOWLEDGE_BASE_DIR\": \"/abs/path\"}\n"
          "   Option 2: 在 openclaw.json 的 env 字段中添加: \"KNOWLEDGE_BASE_DIR\": \"/abs/path/to/knowledge-base\"")
    print("\n❌ 关键检查失败，无法继续后续检查。")
    sys.exit(1)

# Validate absolute path
is_abs = os.path.isabs(kb_raw)
check(is_abs, "KNOWLEDGE_BASE_DIR 格式",
      kb_raw if is_abs else f"非绝对路径: {kb_raw!r}",
      "KNOWLEDGE_BASE_DIR 必须为绝对路径，如 /home/user/project/knowledge-base")
if not is_abs:
    print("\n❌ 路径格式错误，无法继续后续检查。")
    sys.exit(1)

kb = Path(kb_raw)

# ── 3. Directory exists + readable ────────────────────────────────────────────
if not kb.exists():
    print(f"{WARN}  KNOWLEDGE_BASE_DIR 目录不存在: {kb}")
    print(f"   → 可运行初始化脚本创建: python3 \"$SKILL_DIR/scripts/init_dirs.py\"")
    # Not a fatal error — init_dirs.py will create it
else:
    check(kb.is_dir(), "KNOWLEDGE_BASE_DIR 是目录",
          str(kb),
          f"路径已存在但不是目录，请检查: {kb}")
    check(os.access(kb, os.R_OK | os.W_OK), "KNOWLEDGE_BASE_DIR 可读写",
          str(kb),
          f"运行 ls -la {kb.parent} 检查权限；或 chmod 755 {kb}")

# ── 4. openclaw.json check ────────────────────────────────────────────────────
workspace = Path(os.environ.get("SKILL_WORKSPACE", os.getcwd()))
openclaw_paths = [
    workspace / "openclaw.json",
    workspace / ".openclaw" / "openclaw.json",
    Path.home() / "openclaw.json",
]

openclaw_file = next((p for p in openclaw_paths if p.is_file()), None)
if openclaw_file is None:
    print(f"{WARN}  未找到 openclaw.json（搜索路径: {[str(p) for p in openclaw_paths]}）")
    print("   → 请参考 SKILL.md Step 3 配置 openclaw.json")
else:
    check(True, "openclaw.json", str(openclaw_file))
    try:
        with open(openclaw_file, encoding="utf-8") as f:
            cfg = json.load(f)

        # Look for KNOWLEDGE_BASE_DIR in extraPaths
        extra_paths = []
        try:
            defaults = cfg.get("agents", {}).get("defaults", {})
            extra_paths = defaults.get("memorySearch", {}).get("extraPaths", [])
        except (AttributeError, KeyError):
            pass

        kb_in_paths = any(
            str(kb) in str(ep) or "KNOWLEDGE_BASE_DIR" in str(ep)
            for ep in extra_paths
        )
        check(kb_in_paths,
              "openclaw.json: memorySearch.extraPaths 包含 KNOWLEDGE_BASE_DIR",
              "已配置" if kb_in_paths else f"当前 extraPaths: {extra_paths}",
              "在 openclaw.json 中添加: \"extraPaths\": [\"${KNOWLEDGE_BASE_DIR}\"]")
    except json.JSONDecodeError as e:
        check(False, "openclaw.json 格式",
              f"JSON 解析失败: {e}",
              "检查 openclaw.json 是否为合法 JSON 格式")

# ── 5. Standard subdirectory check ────────────────────────────────────────────
if kb.exists() and kb.is_dir():
    missing = [d for d in REQUIRED_DIRS if not (kb / d).is_dir()]
    if missing:
        print(f"{WARN}  以下标准子目录不存在: {', '.join(missing)}")
        print("   → 运行初始化脚本创建: python3 \"$SKILL_DIR/scripts/init_dirs.py\"")
    else:
        check(True, "标准子目录", f"全部 {len(REQUIRED_DIRS)} 个目录已存在")

# ── Summary ───────────────────────────────────────────────────────────────────
print()
if errors:
    print(f"❌ {len(errors)} 项检查未通过: {', '.join(errors)}")
    print("   请按上方提示逐一修复后重新运行本脚本。")
    sys.exit(1)
else:
    print("✅ 所有检查通过。知识库环境已就绪。")
    sys.exit(0)
