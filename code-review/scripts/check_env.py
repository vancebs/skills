#!/usr/bin/env python3
"""
check_env.py — Environment checker for code-review skill.

Checks:
  1. Python >= 3.9
  2. gerrit-api skill is installed (.agents/skills/gerrit-api/)
  3. GERRIT_URL, GERRIT_USERNAME, GERRIT_HTTP_PASSWORD env vars are set
  4. T2MCodingRule skill is installed (.agents/skills/T2MCodingRule/)

Usage:
    python3 scripts/check_env.py [--workspace WORKSPACE]

Exit codes:
    0 — All checks passed
    1 — One or more checks failed
"""

import argparse
import json
import os
import platform
import sys
from pathlib import Path

_OK   = "✅"
_FAIL = "❌"
_WARN = "⚠️ "


def _load_file_config(workspace: str | None = None) -> dict:
    """Load .config/code-review.json from workspace or home."""
    candidates = []
    if workspace:
        candidates.append(Path(workspace) / ".config" / "code-review.json")
    candidates.append(Path.cwd() / ".config" / "code-review.json")
    candidates.append(Path.home() / ".config" / "code-review.json")
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


def check_python():
    v = sys.version_info
    ok = v >= (3, 9)
    suffix = "" if ok else f"  →  需要 Python ≥ 3.9（当前 {v.major}.{v.minor}）"
    print(f"{'✅' if ok else '❌'} Python {v.major}.{v.minor}.{v.micro}{suffix}")
    return ok


def _find_skill(name: str) -> Path | None:
    """Locate a skill directory; tolerates case differences introduced by npx skills."""
    candidates = [name, name.lower(), name.upper()]
    for base in [Path.cwd(), Path.home()]:
        skills_root = base / ".agents" / "skills"
        for variant in candidates:
            p = skills_root / variant
            if p.is_dir():
                return p
        # Fallback: case-insensitive scan of all entries
        if skills_root.is_dir():
            target = name.lower()
            for entry in skills_root.iterdir():
                if entry.is_dir() and entry.name.lower() == target:
                    return entry
    return None


def check_gerrit_api_skill():
    p = _find_skill("gerrit-api")
    if p:
        print(f"{_OK} gerrit-api skill 已安装: {p}")
        return True
    print(f"{_FAIL} gerrit-api skill 未安装（必须安装，code-review 的所有 Gerrit 操作依赖它）")
    print(f"      安装命令: npx skills add https://github.com/vancebs/skills --skill gerrit-api")
    return False


def check_t2mcodingrule_skill():
    p = _find_skill("T2MCodingRule")
    if p:
        print(f"{_OK} T2MCodingRule skill 已安装: {p}")
        return True
    print(f"{_FAIL} T2MCodingRule skill 未安装（必须安装，提供审查规范）")
    print(f"      安装命令: npx skills add https://github.com/vancebs/skills --skill T2MCodingRule")
    return False


def check_gerrit_env_vars(cfg: dict):
    ok = True
    for var in ["GERRIT_URL", "GERRIT_USERNAME", "GERRIT_HTTP_PASSWORD"]:
        val = (cfg.get(var) or os.environ.get(var, "")).strip()
        source = "配置文件" if cfg.get(var) else "环境变量"
        if val:
            display = val if var in ("GERRIT_URL", "GERRIT_USERNAME") else val[:4] + "****"
            print(f"{_OK} {var} = {display}  [{source}]")
        else:
            print(f"{_FAIL} {var} 未设置  →  在配置文件或环境变量中设置 {var}")
            ok = False
    return ok


def check_code_review_config(cfg: dict):
    skip_patterns = (cfg.get("CODE_REVIEW_SKIP_PATTERNS") or os.environ.get("CODE_REVIEW_SKIP_PATTERNS", "")).strip()
    if skip_patterns:
        print(f"{_OK} CODE_REVIEW_SKIP_PATTERNS = {skip_patterns}")
    else:
        print(f"{_WARN} CODE_REVIEW_SKIP_PATTERNS 未设置（默认不过滤额外路径模式）")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", help="Workspace path for config lookup")
    args = parser.parse_args()

    print("=" * 62)
    print("  code-review 环境检查")
    print("=" * 62)
    print(f"\n  系统: {platform.system()} {platform.release()}")
    print()

    cfg = _load_file_config(args.workspace)
    print("─── code-review 配置来源 ─────────────────────────────────")
    if cfg:
        print(f"{_OK} 配置来源: 配置文件（仅 code-review 专属变量）")
    else:
        print(f"{_WARN} 配置来源: 环境变量（未检测到 code-review.json）")

    results = {}

    print("\n─── Python 环境 ──────────────────────────────────────────")
    results["python"] = check_python()

    print("\n─── 依赖 skill ───────────────────────────────────────────")
    results["gerrit_api"] = check_gerrit_api_skill()
    results["t2mcodingrule"] = check_t2mcodingrule_skill()

    print("\n─── Gerrit 环境变量 ──────────────────────────────────────")
    results["gerrit_env"] = check_gerrit_env_vars(cfg)

    print("\n─── code-review 配置 ─────────────────────────────────────")
    check_code_review_config(cfg)

    print("\n" + "=" * 62)
    fails = [k for k, v in results.items() if not v]
    if not fails:
        print("✅ 所有检查通过！可以开始使用 code-review skill。")
        return 0

    print(f"❌ {len(fails)} 项检查未通过: {', '.join(fails)}")
    print("   按上方提示逐一解决后，重新运行本检查。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
