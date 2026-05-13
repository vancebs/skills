#!/usr/bin/env python3
"""
post_result.py — Post code review result to Gerrit.

Called by the LLM agent after completing code review. Posts the review report
as a Gerrit comment and sets the Verified label (0 for PASS, -1 for FAIL).

In test_mode (default), prints the result to stdout without touching Gerrit.

Usage:
    # Inline report
    python3 "$SKILL_DIR/scripts/post_result.py" \\
        --change-id 12345 --result PASS --report "审查通过，代码符合规范"

    # Report from file
    python3 "$SKILL_DIR/scripts/post_result.py" \\
        --change-id 12345 --result FAIL --report-file /tmp/review.txt

    # Report from stdin
    echo "Review text" | python3 "$SKILL_DIR/scripts/post_result.py" \\
        --change-id 12345 --result FAIL

Exit codes:
    0 — Success (posted to Gerrit, or displayed in test_mode)
    1 — Error
    2 — test_mode active — review was displayed but NOT posted to Gerrit
        (set test_mode=false in config, or add --force, to actually post)
"""

import os
import sys
import json
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from base64 import b64encode

_SKILL_NAME      = "agent-code-review"
_CONFIG_FILENAME = "code_review_config.json"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _workspace(args=None):
    if args and getattr(args, "workspace", None):
        return Path(args.workspace).resolve()
    ws = os.environ.get("SKILL_WORKSPACE", "").strip()
    return Path(ws).resolve() if ws else Path.cwd()


def _skill_dir():
    sd = os.environ.get("SKILL_DIR", "").strip()
    if sd:
        return Path(sd).resolve()
    return Path(__file__).resolve().parent.parent


def _load_config(ws, override=None):
    if override:
        p = Path(override)
        if p.is_file():
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        return None
    sd   = _skill_dir()
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
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    return None


# ---------------------------------------------------------------------------
# Gerrit REST
# ---------------------------------------------------------------------------

def _post_review(cfg, change_id, revision, message, verified):
    """
    POST /a/changes/{id}/revisions/{rev}/review
    verified: 0 (PASS) or -1 (FAIL)
    Returns (True, None) on success, (False, error_str) on failure.
    """
    url      = cfg.get("url", "").rstrip("/")
    username = cfg.get("username", "")
    password = cfg.get("password", "")
    creds    = b64encode(f"{username}:{password}".encode()).decode()

    rev      = revision or "current"
    endpoint = f"{url}/a/changes/{change_id}/revisions/{rev}/review"
    body     = json.dumps({
        "message": message,
        "labels":  {"Verified": verified},
        "tag":     "agent-code-review",
    }).encode("utf-8")

    req = Request(endpoint, data=body, headers={
        "Authorization":  f"Basic {creds}",
        "Content-Type":   "application/json",
    })
    req.method = "POST"

    try:
        with urlopen(req, timeout=30):
            return True, None
    except HTTPError as e:
        if e.code == 403:
            return False, ("HTTP 403: 权限不足。"
                           "请确认账号有 Verified 投票权限（Gerrit → 管理员 → 项目权限）")
        if e.code == 401:
            return False, "HTTP 401: 认证失败。请检查 username 和 password 配置"
        return False, f"HTTP {e.code}: {e.reason}"
    except URLError as e:
        return False, f"连接失败: {e.reason}"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Post code review result to Gerrit")
    parser.add_argument("--change-id",   required=True,
                        help="Gerrit change number (e.g. 12345)")
    parser.add_argument("--revision",    default="current",
                        help="Revision SHA or 'current' (default: current)")
    parser.add_argument("--result",      required=True, choices=["PASS", "FAIL"],
                        help="Review outcome")
    parser.add_argument("--report",      help="Review report text (inline)")
    parser.add_argument("--report-file", help="Path to review report file ('-' for stdin)")
    parser.add_argument("--config",      help="Config file path")
    parser.add_argument("--workspace",   help="Project workspace directory")
    parser.add_argument("--force",       action="store_true",
                        help="Ignore test_mode and post to Gerrit")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Print what would be posted without actually posting")
    args = parser.parse_args()

    ws  = _workspace(args)
    cfg = _load_config(ws, args.config)
    if not cfg:
        print("ERROR: 配置文件未找到。请运行 check_env.py 检查环境。", file=sys.stderr)
        return 1

    test_mode = cfg.get("test_mode", True)

    # Read report text
    report = args.report
    if not report:
        if args.report_file == "-":
            report = sys.stdin.read()
        elif args.report_file:
            report = Path(args.report_file).read_text(encoding="utf-8")
        else:
            # Accept from stdin if it's not a terminal (piped input)
            if not sys.stdin.isatty():
                report = sys.stdin.read()
            else:
                print("ERROR: 请通过 --report 或 --report-file 提供 review 报告", file=sys.stderr)
                return 1

    verified = 0 if args.result == "PASS" else -1

    if args.dry_run:
        print(f"[dry-run] change_id={args.change_id}  result={args.result}  "
              f"verified={verified}")
        print(f"[dry-run] report preview:\n{report[:300]}{'...' if len(report) > 300 else ''}")
        return 0

    if test_mode and not args.force:
        print("=" * 62)
        print(f"  [测试模式] Code Review 结果（未提交到 Gerrit）")
        print("=" * 62)
        print(f"  变更:   #{args.change_id}")
        print(f"  结果:   {args.result}  (Verified={verified})")
        print("─" * 62)
        print(report)
        print("─" * 62)
        print("  提示: 将配置中 test_mode 改为 false，或加 --force，即可真实提交")
        return 2

    ok, err = _post_review(cfg, args.change_id, args.revision, report, verified)
    if ok:
        print(f"✅ Review 已提交  →  变更 #{args.change_id}  "
              f"结果: {args.result}  Verified={verified}")
        return 0
    else:
        print(f"❌ 提交失败: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
