#!/usr/bin/env python3
"""
check_env.py — Environment checker for code-review skill.

Verifies that gerrit-api skill is installed and code-review config exists.
Gerrit connectivity is verified by gerrit-api's own check_env.py.

Usage:
    python3 "$SKILL_DIR/scripts/check_env.py"

Exit codes:
    0 — All checks passed
    1 — One or more checks failed
"""

import json
import os
import platform
import sys
from pathlib import Path

_SKILL_NAME      = "code-review"
_CONFIG_FILENAME = "code_review_config.json"
_OK   = "✅"
_FAIL = "❌"
_WARN = "⚠️ "


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _workspace():
    ws = os.environ.get("SKILL_WORKSPACE", "").strip()
    return Path(ws).resolve() if ws else Path.cwd()


def _skill_dir():
    sd = os.environ.get("SKILL_DIR", "").strip()
    return Path(sd).resolve() if sd else Path(__file__).resolve().parent.parent


def _find_config():
    ws = _workspace()
    sd = _skill_dir()
    home = Path.home()
    for p in [
        ws   / "config" / _SKILL_NAME / _CONFIG_FILENAME,
        ws   / "config" / _CONFIG_FILENAME,
        ws   /            _CONFIG_FILENAME,
        sd   /            _CONFIG_FILENAME,
        home / ".config" / _SKILL_NAME / _CONFIG_FILENAME,
        home / ".config" / _CONFIG_FILENAME,
        home /             _CONFIG_FILENAME,
    ]:
        if p.is_file():
            return p
    return None


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_python():
    v = sys.version_info
    ok = v >= (3, 9)
    suffix = "" if ok else f"  →  需要 Python ≥ 3.9（当前 {v.major}.{v.minor}）"
    print(f"{'✅' if ok else '❌'} Python {v.major}.{v.minor}.{v.micro}{suffix}")
    return ok


def check_gerrit_api_skill():
    """Check gerrit-api skill is installed; print install command if missing."""
    ws   = _workspace()
    home = Path.home()
    candidates = [
        ws   / ".agents" / "skills" / "gerrit-api",
        home / ".agents" / "skills" / "gerrit-api",
    ]
    for p in candidates:
        if p.is_dir():
            print(f"{_OK} gerrit-api skill 已安装: {p}")
            # Also check GERRIT_API_SKILL_DIR env var
            gsd = os.environ.get("GERRIT_API_SKILL_DIR", "").strip()
            if not gsd:
                print(f"{_WARN}  GERRIT_API_SKILL_DIR 未设置  →  建议设置为: {p}")
                print(f"       Linux/macOS:  export GERRIT_API_SKILL_DIR=\"{p}\"")
                print(f"       PowerShell:   $env:GERRIT_API_SKILL_DIR = \"{p}\"")
            else:
                print(f"{_OK} GERRIT_API_SKILL_DIR: {gsd}")
            return True

    print(f"{_FAIL} gerrit-api skill 未安装（必须安装，code-review 的所有 Gerrit 操作依赖它）")
    print(f"      安装命令: npx skills add https://github.com/vancebs/skills --skill gerrit-api")
    print(f"      安装后运行 gerrit-api 的 check_env.py 配置 Gerrit 连接：")
    print(f"        python3 \"$GERRIT_API_SKILL_DIR/scripts/check_env.py\"")
    return False


def check_config():
    cfg_path = _find_config()
    if not cfg_path:
        ws  = _workspace()
        sd  = _skill_dir()
        dst = ws / "config" / _SKILL_NAME / _CONFIG_FILENAME
        src = sd / "scripts" / "config.json.example"
        print(f"{_FAIL} code-review 配置文件未找到  →  请创建：")
        print(f"      # Linux / macOS:")
        print(f"      mkdir -p \"{ws / 'config' / _SKILL_NAME}\"")
        print(f"      cp \"{src}\" \"{dst}\"")
        print(f"      # Windows PowerShell:")
        print(f"      New-Item -ItemType Directory -Force \"{ws / 'config' / _SKILL_NAME}\"")
        print(f"      Copy-Item \"{src}\" \"{dst}\"")
        return None, False

    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        print(f"{_OK} code-review 配置文件: {cfg_path}")
        tm = cfg.get("test_mode", True)
        print(f"     test_mode = {tm}  {'（仅打印报告，不写 Gerrit）' if tm else '（将发布到 Gerrit）'}")
        return cfg, True
    except json.JSONDecodeError as e:
        print(f"{_FAIL} 配置文件 JSON 格式错误: {e}")
        return None, False


def check_workspace_writable():
    ws   = _workspace()
    test = ws / ".cr_write_test"
    try:
        test.write_text("ok")
        test.unlink()
        print(f"{_OK} Workspace 可写: {ws}")
        return True
    except Exception as e:
        print(f"{_FAIL} Workspace 不可写: {ws}  ({e})")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 62)
    print("  code-review 环境检查")
    print("=" * 62)
    print(f"\n  系统:            {platform.system()} {platform.release()}")
    print(f"  SKILL_WORKSPACE: {_workspace()}")
    print(f"  SKILL_DIR:       {_skill_dir()}")
    print()

    results = {}

    print("─── Python 环境 ──────────────────────────────────────────")
    results["python"] = check_python()

    print("\n─── gerrit-api skill（必须）──────────────────────────────")
    results["gerrit_api"] = check_gerrit_api_skill()

    print("\n─── code-review 配置文件 ─────────────────────────────────")
    _, results["config"] = check_config()

    print("\n─── Workspace 写权限 ─────────────────────────────────────")
    results["workspace"] = check_workspace_writable()

    print("\n" + "=" * 62)
    fails = [k for k, v in results.items() if not v]
    if not fails:
        print("✅ 所有检查通过！可以开始使用 code-review skill。")
        print()
        print("   提示: 运行 gerrit-api 的环境检查以验证 Gerrit 连接：")
        gsd = os.environ.get("GERRIT_API_SKILL_DIR", "").strip()
        if gsd:
            print(f"     python3 \"{gsd}/scripts/check_env.py\"")
        else:
            print(f"     python3 \"$GERRIT_API_SKILL_DIR/scripts/check_env.py\"")
        return 0
    else:
        print(f"❌ {len(fails)} 项检查未通过: {', '.join(fails)}")
        print("   按上方提示逐一解决后，重新运行本检查。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
