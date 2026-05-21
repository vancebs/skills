#!/usr/bin/env python3
"""
check_env.py — Environment checker for gerrit-api skill.

Checks:
  1. Python >= 3.9
  2. GERRIT_URL, GERRIT_USERNAME, GERRIT_HTTP_PASSWORD are configured
     (config file takes priority over env vars)
  3. GERRIT_DISABLE_SSL_VERIFY value (optional, informational)
  4. SSH available (required for stream-events only)

Usage:
    python3 scripts/check_env.py [--workspace WORKSPACE]

Exit codes:
    0 — All required checks passed
    1 — One or more required checks failed
"""

import argparse
import json
import os
import platform
import shutil
import sys
from pathlib import Path

_OK   = "✅"
_FAIL = "❌"
_WARN = "⚠️ "


def _load_file_config(workspace: str | None = None) -> tuple[dict, str | None]:
    """Load gerrit-api.json; return (cfg_dict, path_used_or_None)."""
    candidates = []
    if workspace:
        candidates.append(Path(workspace) / ".config" / "gerrit-api.json")
    candidates.append(Path.cwd() / ".config" / "gerrit-api.json")
    candidates.append(Path.home() / ".config" / "gerrit-api.json")

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
                if isinstance(d, dict):
                    return d, str(path)
            except (json.JSONDecodeError, OSError):
                pass
    return {}, None


def check_python() -> bool:
    v = sys.version_info
    ok = v >= (3, 9)
    suffix = "" if ok else f"  →  需要 Python ≥ 3.9（当前 {v.major}.{v.minor}）"
    print(f"{'✅' if ok else '❌'} Python {v.major}.{v.minor}.{v.micro}{suffix}")
    return ok


def check_credentials(cfg: dict, cfg_path: str | None) -> bool:
    source = f"配置文件 ({cfg_path})" if cfg_path else "环境变量"
    ok = True
    for var in ["GERRIT_URL", "GERRIT_USERNAME", "GERRIT_HTTP_PASSWORD"]:
        val = (cfg.get(var) or os.environ.get(var, "")).strip()
        var_source = f"配置文件" if cfg.get(var) else "环境变量"
        if val:
            display = val if var != "GERRIT_HTTP_PASSWORD" else val[:4] + "****"
            print(f"{_OK} {var} = {display}  [{var_source}]")
        else:
            print(f"{_FAIL} {var} 未设置")
            if var == "GERRIT_URL":
                print(f"   → 在配置文件或环境变量中设置: export GERRIT_URL=https://gerrit.example.com")
            elif var == "GERRIT_USERNAME":
                print(f"   → 在配置文件或环境变量中设置: export GERRIT_USERNAME=john.doe")
            elif var == "GERRIT_HTTP_PASSWORD":
                print(f"   → 在配置文件或环境变量中设置: export GERRIT_HTTP_PASSWORD=<token>")
                print(f"   → 生成位置: Gerrit → Settings → HTTP Credentials → Generate Password")
            ok = False
    return ok


def check_ssl_config(cfg: dict) -> bool:
    val = (cfg.get("GERRIT_DISABLE_SSL_VERIFY") or os.environ.get("GERRIT_DISABLE_SSL_VERIFY", "false")).strip().lower()
    source = "配置文件" if cfg.get("GERRIT_DISABLE_SSL_VERIFY") else "环境变量/默认"
    if val == "true":
        print(f"{_WARN} GERRIT_DISABLE_SSL_VERIFY = true  [{source}]  — SSL 证书验证已关闭")
    else:
        print(f"{_OK} GERRIT_DISABLE_SSL_VERIFY = false  [{source}]  — 使用 Python 默认 SSL 验证")
    return True


def check_ssh() -> bool:
    found = shutil.which("ssh")
    if found:
        print(f"{_OK} ssh 已安装: {found}（stream-events 可用）")
        return True
    print(f"{_WARN} ssh 未找到（仅影响 stream-events；REST API 不需要 ssh）")
    return True  # Not a hard requirement


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", help="Workspace path for config file lookup")
    args = parser.parse_args()

    print("=" * 62)
    print("  gerrit-api 环境检查")
    print("=" * 62)
    print(f"\n  系统: {platform.system()} {platform.release()}")
    print()

    cfg, cfg_path = _load_file_config(args.workspace)
    if cfg_path:
        print(f"{_OK} 配置来源: 配置文件 → {cfg_path}")
    else:
        print(f"{_WARN} 未检测到配置文件，将从环境变量读取")
        print(f"   → 可选: 创建 $WORKSPACE/.config/gerrit-api.json 或 ~/.config/gerrit-api.json")

    results = {}

    print("\n─── Python 环境 ──────────────────────────────────────────")
    results["python"] = check_python()

    print("\n─── Gerrit 凭据 ──────────────────────────────────────────")
    results["credentials"] = check_credentials(cfg, cfg_path)

    print("\n─── SSL 配置 ─────────────────────────────────────────────")
    check_ssl_config(cfg)

    print("\n─── SSH（stream-events）──────────────────────────────────")
    check_ssh()

    print("\n" + "=" * 62)
    fails = [k for k, v in results.items() if not v]
    if not fails:
        print("✅ 所有检查通过！可以开始使用 gerrit-api skill。")
        return 0

    print(f"❌ {len(fails)} 项检查未通过: {', '.join(fails)}")
    print("   按上方提示逐一解决后，重新运行本检查。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
