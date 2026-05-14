#!/usr/bin/env python3
"""
fetch_patch.py — Fetch Gerrit patch data for code review.

Accepts any of the following identifiers and fetches the corresponding
change details, commit message, file list and diffs from Gerrit REST API.

Accepted inputs (at least one required):
    --url URL          Gerrit change page URL (http or https)
    --change-id ID     Gerrit Change-Id (I<40hex>) or change number (digits)
    --commit-id SHA    Commit SHA (full 40-char or short ≥7 chars)
    --event-json TEXT  Raw Gerrit stream event JSON text

Output (stdout): JSON object — see schema below.
Errors (stderr): plain text.

Exit codes:
    0 — Success, JSON written to stdout
    1 — Error (details on stderr)

Output JSON schema:
{
  "status":         "ok" | "error",
  "message":        "<error detail when status==error>",
  "change_number":  12345,
  "change_id":      "Iabc...40hex",
  "revision":       "abc123...40hex",
  "patchset_number": 1,
  "project":        "org/repo",
  "branch":         "main",
  "subject":        "Fix login bug",
  "uploader":       "john.doe",
  "commit_message": "Fix login bug\\n\\nChange-Id: I...",
  "files": [
    {
      "path":   "src/main/java/Foo.java",
      "status": "MODIFIED",
      "diff":   "unified diff text"
    }
  ]
}
"""

import argparse
import base64
import json
import os
import re
import ssl
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

_SKILL_NAME      = "code-review"
_CONFIG_FILENAME = "code_review_config.json"


# ---------------------------------------------------------------------------
# Path / config helpers
# ---------------------------------------------------------------------------

def _workspace(args=None):
    if args and getattr(args, "workspace", None):
        return Path(args.workspace).resolve()
    ws = os.environ.get("SKILL_WORKSPACE", "").strip()
    return Path(ws).resolve() if ws else Path.cwd()


def _skill_dir():
    sd = os.environ.get("SKILL_DIR", "").strip()
    return Path(sd).resolve() if sd else Path(__file__).resolve().parent.parent


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
# SSL helpers
# ---------------------------------------------------------------------------

def _ssl_noverify_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _is_ssl_error(exc):
    reason = getattr(exc, "reason", None)
    if isinstance(reason, ssl.SSLError):
        return True
    if isinstance(exc, ssl.SSLError):
        return True
    return "ssl" in str(exc).lower() or "certificate" in str(exc).lower()


# ---------------------------------------------------------------------------
# Gerrit REST helpers
# ---------------------------------------------------------------------------

def _auth_header(username, password):
    creds = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {creds}"


def _strip_xssi(text):
    return text[5:] if text.startswith(")]}'\n") else text


def _http_get(url, username, password):
    """GET with auth; auto-retries with SSL disabled on certificate errors."""
    req = Request(url, headers={"Authorization": _auth_header(username, password)})

    def _do(ctx=None):
        with urlopen(req, timeout=20, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="replace")

    try:
        return _do()
    except URLError as e:
        if _is_ssl_error(e):
            print(f"警告: SSL 验证失败，禁用 SSL 验证后重试 ({url})", file=sys.stderr)
            return _do(ctx=_ssl_noverify_context())
        raise


def _get_json(base_url, endpoint, username, password):
    url = f"{base_url}/a{endpoint}"
    raw = _http_get(url, username, password)
    return json.loads(_strip_xssi(raw))


# ---------------------------------------------------------------------------
# Input parsers
# ---------------------------------------------------------------------------

_RE_CHANGE_ID   = re.compile(r"^I[0-9a-f]{40}$")
_RE_CHANGE_NUM  = re.compile(r"^\d+$")
_RE_COMMIT_SHA  = re.compile(r"^[0-9a-f]{7,40}$")


def _parse_url(url_str):
    """
    Extract (change_number, patchset_number) from a Gerrit change page URL.

    Supported URL patterns:
      New-style:  /c/{project}/+/{NUMBER}[/{PATCHSET}]
      Old-style:  /#/c/{NUMBER}[/{PATCHSET}]
      Short:      /c/{NUMBER}
    Returns (change_number:int|None, patchset_number:int|None).
    """
    # New-style: /c/.../+/NUMBER[/PATCHSET]
    m = re.search(r"/c/[^#?]+/\+/(\d+)(?:/(\d+))?", url_str)
    if m:
        ps = int(m.group(2)) if m.group(2) else None
        return int(m.group(1)), ps

    # Old-style: #/c/NUMBER[/PATCHSET]
    m = re.search(r"#/c/(\d+)(?:/(\d+))?", url_str)
    if m:
        ps = int(m.group(2)) if m.group(2) else None
        return int(m.group(1)), ps

    # Fallback: /c/NUMBER
    m = re.search(r"/c/(\d+)", url_str)
    if m:
        return int(m.group(1)), None

    return None, None


def _parse_event_json(text):
    """
    Extract (change_number, revision, patchset_number) from Gerrit stream event JSON.

    Supported event types (all include change.number):
      patchset-created, patchset-updated, comment-added, change-merged,
      reviewer-added, vote-deleted, wip-state-changed, private-state-changed.
    Returns (change_number:int|None, revision:str|None, patchset_number:int|None).
    """
    try:
        ev = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"event-json 不是合法 JSON: {e}") from e

    change = ev.get("change", {})
    patchset = ev.get("patchSet", {})

    change_number = change.get("number")
    if isinstance(change_number, str) and change_number.isdigit():
        change_number = int(change_number)

    revision = patchset.get("revision") or patchset.get("ref")
    ps_num   = patchset.get("number")

    # refUpdated events don't have a change — return None
    if not change_number:
        return None, None, None

    return change_number, revision, ps_num


# ---------------------------------------------------------------------------
# Gerrit fetch logic
# ---------------------------------------------------------------------------

def _get_change_by_number(base_url, change_number, username, password):
    """Fetch change detail by numeric change ID."""
    ep = f"/changes/{change_number}?o=CURRENT_REVISION&o=CURRENT_COMMIT"
    return _get_json(base_url, ep, username, password)


def _get_change_by_id(base_url, change_id, username, password):
    """Fetch change detail by Change-Id (I<40hex>) — returns first result."""
    q = quote(f"change:{change_id}", safe="")
    ep = f"/changes/?q={q}&o=CURRENT_REVISION&o=CURRENT_COMMIT"
    results = _get_json(base_url, ep, username, password)
    if not results:
        raise ValueError(f"未找到 Change-Id={change_id} 对应的变更")
    return results[0]


def _get_change_by_commit(base_url, commit_sha, username, password):
    """Fetch change detail by commit SHA."""
    q = quote(f"commit:{commit_sha}", safe="")
    ep = f"/changes/?q={q}&o=CURRENT_REVISION&o=CURRENT_COMMIT"
    results = _get_json(base_url, ep, username, password)
    if not results:
        raise ValueError(f"未找到 commit={commit_sha} 对应的变更")
    return results[0]


def _get_files_and_diffs(base_url, change_number, revision, username, password,
                         skip_patterns=None):
    """Fetch files list and unified diffs for the given revision."""
    import fnmatch

    skip_patterns = skip_patterns or []

    # List files
    ep = f"/changes/{change_number}/revisions/{revision}/files/"
    files_map = _get_json(base_url, ep, username, password)

    results = []
    for path, info in files_map.items():
        if path == "/COMMIT_MSG":
            continue  # already captured as commit_message

        # Apply skip patterns
        if any(fnmatch.fnmatch(path, pat) for pat in skip_patterns):
            continue

        status = info.get("status", "MODIFIED")

        # Fetch diff
        diff_text = ""
        try:
            diff_ep = (f"/changes/{change_number}/revisions/{revision}"
                       f"/files/{quote(path, safe='')}/diff?intraline=false")
            diff_obj = _get_json(base_url, diff_ep, username, password)
            diff_text = _format_diff(path, diff_obj)
        except Exception as e:
            diff_text = f"<diff fetch error: {e}>"

        results.append({
            "path":   path,
            "status": status,
            "diff":   diff_text,
        })

    return results


def _format_diff(path, diff_obj):
    """Convert Gerrit's diff JSON into a unified-diff-like text."""
    lines = [f"--- a/{path}", f"+++ b/{path}"]
    for section in diff_obj.get("content", []):
        # Each section is one of: {a: [...], b: [...], ab: [...]}
        if "ab" in section:
            for line in section["ab"]:
                lines.append(f" {line}")
        if "a" in section:
            for line in section["a"]:
                lines.append(f"-{line}")
        if "b" in section:
            for line in section["b"]:
                lines.append(f"+{line}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def _resolve_change(args, cfg):
    """
    Resolve the input to a (change_detail, patchset_number, explicit_revision) tuple.
    Tries inputs in this order: --url, --event-json, --change-id, --commit-id.
    """
    base_url = cfg["url"].rstrip("/")
    username = cfg["username"]
    password = cfg["password"]

    explicit_revision = None
    patchset_number   = None

    if args.url:
        change_num, patchset_number = _parse_url(args.url)
        if change_num is None:
            raise ValueError(
                f"无法从 URL 中解析 change number。"
                f"期望格式: https://gerrit.host/c/project/+/NUMBER\n"
                f"实际 URL: {args.url}"
            )
        detail = _get_change_by_number(base_url, change_num, username, password)

    elif args.event_json:
        change_num, explicit_revision, patchset_number = _parse_event_json(args.event_json)
        if change_num is None:
            raise ValueError(
                "event-json 中未找到 change.number。"
                "仅支持含 change 对象的事件类型（patchset-created、comment-added 等）"
            )
        detail = _get_change_by_number(base_url, change_num, username, password)

    elif args.change_id:
        cid = args.change_id.strip()
        if _RE_CHANGE_NUM.match(cid):
            detail = _get_change_by_number(base_url, int(cid), username, password)
        elif _RE_CHANGE_ID.match(cid):
            detail = _get_change_by_id(base_url, cid, username, password)
        else:
            raise ValueError(
                f"无效的 change-id 格式: {cid!r}\n"
                f"期望格式: 纯数字（如 12345）或 I+40位十六进制（如 Iabcdef...）\n"
                f"正则: ^(\\d+|I[0-9a-f]{{40}})$"
            )

    elif args.commit_id:
        sha = args.commit_id.strip().lower()
        if not _RE_COMMIT_SHA.match(sha):
            raise ValueError(
                f"无效的 commit-id 格式: {sha!r}\n"
                f"期望: 7~40 位十六进制字符串\n"
                f"正则: ^[0-9a-f]{{7,40}}$"
            )
        detail = _get_change_by_commit(base_url, sha, username, password)
        # Extract revision from search result
        revs = detail.get("revisions", {})
        if revs:
            explicit_revision = next(iter(revs))

    else:
        raise ValueError("必须提供以下参数之一：--url, --change-id, --commit-id, --event-json")

    return detail, patchset_number, explicit_revision


def fetch_patch(args, cfg):
    detail, patchset_number, explicit_revision = _resolve_change(args, cfg)

    base_url = cfg["url"].rstrip("/")
    username = cfg["username"]
    password = cfg["password"]

    change_number = detail.get("_number")
    change_id     = detail.get("change_id", "")
    project       = detail.get("project", "")
    branch        = detail.get("branch", "")
    subject       = detail.get("subject", "")
    uploader      = (detail.get("owner", {}).get("username")
                     or detail.get("owner", {}).get("name", ""))

    # Determine revision to use
    revisions = detail.get("revisions", {})
    if explicit_revision and explicit_revision in revisions:
        revision = explicit_revision
    elif revisions:
        # Use the highest patchset number if patchset_number was specified
        if patchset_number:
            revision = next(
                (sha for sha, rv in revisions.items()
                 if rv.get("_number") == patchset_number),
                next(iter(revisions))
            )
        else:
            revision = next(iter(revisions))
    else:
        raise ValueError("无法确定 revision，change 中没有 revisions 信息")

    rev_info       = revisions.get(revision, {})
    patchset_number = patchset_number or rev_info.get("_number", 1)
    commit_obj     = rev_info.get("commit", {})
    commit_message = commit_obj.get("message", "")

    # Fetch files and diffs
    skip_patterns = cfg.get("skip_file_patterns", [])
    files = _get_files_and_diffs(
        base_url, change_number, revision, username, password,
        skip_patterns=skip_patterns,
    )

    return {
        "status":          "ok",
        "change_number":   change_number,
        "change_id":       change_id,
        "revision":        revision,
        "patchset_number": patchset_number,
        "project":         project,
        "branch":          branch,
        "subject":         subject,
        "uploader":        uploader,
        "commit_message":  commit_message,
        "files":           files,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fetch Gerrit patch data for code review",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 fetch_patch.py --url https://gerrit.example.com/c/proj/+/12345\n"
            "  python3 fetch_patch.py --change-id 12345\n"
            "  python3 fetch_patch.py --change-id Iabcdef1234567890abcdef1234567890abcdef12\n"
            "  python3 fetch_patch.py --commit-id abc123def456\n"
            "  python3 fetch_patch.py --event-json '{\"type\":\"patchset-created\",...}'\n"
        ),
    )
    parser.add_argument("--url",         help="Gerrit change page URL")
    parser.add_argument("--change-id",   help="Change-Id (I<40hex>) or change number")
    parser.add_argument("--commit-id",   help="Commit SHA (7~40 hex chars)")
    parser.add_argument("--event-json",  help="Raw Gerrit stream event JSON text")
    parser.add_argument("--workspace",   help="Project workspace directory")
    parser.add_argument("--config",      help="Config file path (override search)")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Print resolved identifiers without fetching diffs")
    args = parser.parse_args()

    if not any([args.url, args.change_id, args.commit_id, args.event_json]):
        parser.error("必须提供以下参数之一：--url, --change-id, --commit-id, --event-json")

    ws  = _workspace(args)
    cfg = _load_config(ws, args.config)
    if not cfg:
        print(json.dumps({
            "status":  "error",
            "message": "配置文件未找到。请运行 check_env.py 检查环境并创建配置文件。",
        }), file=sys.stderr)
        return 1

    required = ["url", "username", "password"]
    missing  = [k for k in required if not cfg.get(k, "")]
    if missing:
        print(json.dumps({
            "status":  "error",
            "message": f"配置缺少必填项: {missing}。请编辑配置文件填写完整。",
        }), file=sys.stderr)
        return 1

    try:
        if args.dry_run:
            detail, ps, rev = _resolve_change(args, cfg)
            print(json.dumps({
                "status":        "dry_run",
                "change_number": detail.get("_number"),
                "change_id":     detail.get("change_id"),
                "subject":       detail.get("subject"),
                "patchset":      ps,
                "revision":      rev,
            }, ensure_ascii=False, indent=2))
            return 0

        result = fetch_patch(args, cfg)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    except (HTTPError, URLError) as e:
        msg = f"Gerrit API 连接错误: {e}"
        print(json.dumps({"status": "error", "message": msg}), file=sys.stderr)
        return 1
    except ValueError as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        return 1
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"未知错误: {e}"}),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
