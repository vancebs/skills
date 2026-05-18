#!/usr/bin/env python3
"""
check_env.py — t2-config environment checker

Checks:
  1. Python version ≥ 3.9
  2. CFG_DIR env var is set
  3. CFG_DIR path exists and is writable (creates it if missing)

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
"""

import os
import sys
from pathlib import Path


def _ok(label: str, detail: str) -> None:
    print(f"✅ {label}: {detail}")


def _fail(label: str, problem: str, fix: str) -> None:
    print(f"❌ {label}: {problem}\n   → 解决方法: {fix}")


def main() -> int:
    failures = 0

    # 1. Python version
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 9):
        _ok("Python 版本", f"{major}.{minor} (≥ 3.9 ✓)")
    else:
        _fail(
            "Python 版本",
            f"{major}.{minor} (需要 ≥ 3.9)",
            "升级 Python: https://www.python.org/downloads/"
        )
        failures += 1

    # 2. CFG_DIR is set
    cfg_dir_raw = os.environ.get("CFG_DIR", "").strip()
    if not cfg_dir_raw:
        _fail(
            "CFG_DIR",
            "未设置",
            'export CFG_DIR="$(pwd)/config"  (Linux/macOS) | '
            "set CFG_DIR=%CD%\\config  (Windows CMD) | "
            '$env:CFG_DIR = "$(Get-Location)\\config"  (PowerShell)'
        )
        failures += 1
        # Cannot check path if not set
        return failures

    _ok("CFG_DIR", cfg_dir_raw)

    # 3. CFG_DIR exists / writable
    cfg_dir = Path(cfg_dir_raw)
    if not cfg_dir.exists():
        try:
            cfg_dir.mkdir(parents=True, exist_ok=True)
            _ok("CFG_DIR 目录", f"已创建: {cfg_dir}")
        except OSError as e:
            _fail(
                "CFG_DIR 目录",
                f"无法创建 {cfg_dir}: {e}",
                "检查父目录权限，或手动创建: mkdir -p \"$CFG_DIR\""
            )
            failures += 1
            return failures
    elif not cfg_dir.is_dir():
        _fail(
            "CFG_DIR",
            f"{cfg_dir} 已存在但不是目录",
            "删除该文件并重新设置 CFG_DIR"
        )
        failures += 1
        return failures
    else:
        _ok("CFG_DIR 目录", f"已存在: {cfg_dir}")

    # writable check
    test_file = cfg_dir / ".write_test"
    try:
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        _ok("CFG_DIR 写权限", "可写 ✓")
    except OSError as e:
        _fail(
            "CFG_DIR 写权限",
            f"目录不可写: {e}",
            f"检查权限: ls -la \"{cfg_dir.parent}\"  或  chmod 755 \"{cfg_dir}\""
        )
        failures += 1

    return failures


if __name__ == "__main__":
    sys.exit(main())
