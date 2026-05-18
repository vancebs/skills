#!/usr/bin/env python3
"""
gerrit_api.py — Gerrit REST API helper (cross-platform, Python 3.9+)

Pure-Python implementation that works on Windows, Linux, and macOS without
any extra dependencies (uses only the Python standard library: urllib, json,
base64, pathlib).

Credentials are read exclusively from environment variables:
  GERRIT_URL              Gerrit base URL (required), e.g. https://gerrit.example.com
  GERRIT_USERNAME         Gerrit username (required)
  GERRIT_HTTP_PASSWORD    HTTP credential token (required)
                          Generate at: Gerrit → Settings → HTTP Credentials

Usage:
  python gerrit_api.py <command> [args...]

Commands:
  query         <query-string> [OPTION ...]   Query for changes
  get-change    <change-id> [OPTION ...]       Get change details
  list-files    <change-id> [revision]         List modified files
  get-diff      <change-id> <file> [revision]  Get file diff
  get-content   <change-id> <file> [revision]  Get raw file content (stdout)
  create-draft  <change-id> <revision> <json>  Create a draft comment
  review        <change-id> <revision> <json>  Post a review
  submit        <change-id>                    Submit a change
  abandon       <change-id> [message]          Abandon a change
  restore       <change-id> [message]          Restore a change
  add-reviewer  <change-id> <account>          Add a reviewer
  set-topic     <change-id> <topic>            Set the topic
  help                                         Show this help
"""

import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import warnings


def _ssl_noverify_context() -> ssl.SSLContext:
    """Return an SSL context that skips certificate verification."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _is_ssl_error(exc: Exception) -> bool:
    """Return True if the exception is SSL-related."""
    reason = getattr(exc, "reason", None)
    if isinstance(reason, ssl.SSLError):
        return True
    if isinstance(exc, ssl.SSLError):
        return True
    msg = str(exc).lower()
    return "ssl" in msg or "certificate" in msg


# ─── Config loading ───────────────────────────────────────────────────────────

def load_config() -> tuple[str, str, str]:
    """Return (url, username, password) from environment variables."""
    url      = os.environ.get("GERRIT_URL", "").strip().rstrip("/")
    username = os.environ.get("GERRIT_USERNAME", "").strip()
    password = os.environ.get("GERRIT_HTTP_PASSWORD", "").strip()

    if not url:
        _die("GERRIT_URL is not set.\n  → export GERRIT_URL=\"https://gerrit.example.com\"")
    if not username:
        _die("GERRIT_USERNAME is not set.\n  → export GERRIT_USERNAME=\"john.doe\"")
    if not password:
        _die("GERRIT_HTTP_PASSWORD is not set.\n  → export GERRIT_HTTP_PASSWORD=\"your-http-token\"\n  (Generate at: Gerrit → Settings → HTTP Credentials)")

    return url, username, password


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def _strip_xssi(body: str) -> str:
    """Strip the Gerrit XSSI prevention prefix )]}' from the response body."""
    if body.startswith(")]}'\n"):
        return body[5:]
    return body


def _http(method: str, url: str, username: str, password: str,
          body: dict | None = None) -> str:
    """Perform an authenticated HTTP request; return raw response body.

    On SSL verification failure, automatically retries once with SSL
    verification disabled and emits a warning.
    """
    headers = {"Authorization": _auth_header(username, password)}
    data: bytes | None = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    def _do_request(ctx=None):
        with urllib.request.urlopen(req, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="replace")

    try:
        return _do_request()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        _die(f"HTTP {e.code} {e.reason}\n{detail}")
    except urllib.error.URLError as e:
        if _is_ssl_error(e):
            warnings.warn(
                f"SSL verification failed for {url}; retrying with SSL verification disabled.",
                stacklevel=2,
            )
            try:
                return _do_request(ctx=_ssl_noverify_context())
            except urllib.error.HTTPError as e2:
                detail = e2.read().decode("utf-8", errors="replace")
                _die(f"HTTP {e2.code} {e2.reason}\n{detail}")
            except urllib.error.URLError as e2:
                _die(f"Connection error (SSL disabled): {e2.reason}")
        _die(f"Connection error: {e.reason}")


def _http_bytes(url: str, username: str, password: str) -> bytes:
    """GET raw bytes (used for base64-encoded file content).

    On SSL verification failure, automatically retries once with SSL
    verification disabled and emits a warning.
    """
    headers = {"Authorization": _auth_header(username, password)}
    req = urllib.request.Request(url, headers=headers)

    def _do_request(ctx=None):
        with urllib.request.urlopen(req, context=ctx) as resp:
            return resp.read()

    try:
        return _do_request()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        _die(f"HTTP {e.code} {e.reason}\n{detail}")
    except urllib.error.URLError as e:
        if _is_ssl_error(e):
            warnings.warn(
                f"SSL verification failed for {url}; retrying with SSL verification disabled.",
                stacklevel=2,
            )
            try:
                return _do_request(ctx=_ssl_noverify_context())
            except urllib.error.HTTPError as e2:
                detail = e2.read().decode("utf-8", errors="replace")
                _die(f"HTTP {e2.code} {e2.reason}\n{detail}")
            except urllib.error.URLError as e2:
                _die(f"Connection error (SSL disabled): {e2.reason}")
        _die(f"Connection error: {e.reason}")


def _get(base_url: str, endpoint: str, username: str, password: str) -> dict | list:
    url = f"{base_url}/a{endpoint}"
    raw = _http("GET", url, username, password)
    return json.loads(_strip_xssi(raw))


def _post(base_url: str, endpoint: str, username: str, password: str,
          body: dict | None = None) -> dict | list | None:
    url = f"{base_url}/a{endpoint}"
    raw = _http("POST", url, username, password, body or {})
    text = _strip_xssi(raw).strip()
    return json.loads(text) if text else None


def _put(base_url: str, endpoint: str, username: str, password: str,
         body: dict | None = None) -> dict | list | None:
    url = f"{base_url}/a{endpoint}"
    raw = _http("PUT", url, username, password, body or {})
    text = _strip_xssi(raw).strip()
    return json.loads(text) if text else None


# ─── Utility ─────────────────────────────────────────────────────────────────

def _die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _out(data: dict | list | None) -> None:
    if data is None:
        return
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _url_encode(s: str) -> str:
    return urllib.parse.quote(s, safe="")


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_query(base_url: str, username: str, password: str, args: list[str]) -> None:
    """query <query-string> [OPTION ...]"""
    if not args:
        _die("Usage: query <query-string> [OPTION ...]")
    query = args[0]
    opts = "".join(f"&o={o}" for o in args[1:])
    _out(_get(base_url, f"/changes/?q={query}&n=25{opts}", username, password))


def cmd_get_change(base_url: str, username: str, password: str, args: list[str]) -> None:
    """get-change <change-id> [OPTION ...]"""
    if not args:
        _die("Usage: get-change <change-id> [OPTION ...]")
    change_id = args[0]
    opts_list = args[1:] if len(args) > 1 else ["CURRENT_REVISION", "DETAILED_LABELS", "DETAILED_ACCOUNTS"]
    opts = "".join(f"&o={o}" for o in opts_list)
    _out(_get(base_url, f"/changes/{change_id}?{opts}", username, password))


def cmd_list_files(base_url: str, username: str, password: str, args: list[str]) -> None:
    """list-files <change-id> [revision]"""
    if not args:
        _die("Usage: list-files <change-id> [revision]")
    change_id = args[0]
    revision = args[1] if len(args) > 1 else "current"
    _out(_get(base_url, f"/changes/{change_id}/revisions/{revision}/files/", username, password))


def cmd_get_diff(base_url: str, username: str, password: str, args: list[str]) -> None:
    """get-diff <change-id> <file-path> [revision]"""
    if len(args) < 2:
        _die("Usage: get-diff <change-id> <file-path> [revision]")
    change_id = args[0]
    file_path = _url_encode(args[1])
    revision = args[2] if len(args) > 2 else "current"
    _out(_get(base_url, f"/changes/{change_id}/revisions/{revision}/files/{file_path}/diff",
              username, password))


def cmd_get_content(base_url: str, username: str, password: str, args: list[str]) -> None:
    """get-content <change-id> <file-path> [revision]  →  raw file content to stdout"""
    if len(args) < 2:
        _die("Usage: get-content <change-id> <file-path> [revision]")
    change_id = args[0]
    file_path = _url_encode(args[1])
    revision = args[2] if len(args) > 2 else "current"
    url = f"{base_url}/a/changes/{change_id}/revisions/{revision}/files/{file_path}/content"
    raw_b64 = _http_bytes(url, username, password)
    content = base64.b64decode(raw_b64)
    sys.stdout.buffer.write(content)


def cmd_create_draft(base_url: str, username: str, password: str, args: list[str]) -> None:
    """create-draft <change-id> <revision> <json-body>"""
    if len(args) < 3:
        _die("Usage: create-draft <change-id> <revision> <json-body>")
    change_id, revision, json_body = args[0], args[1], args[2]
    try:
        body = json.loads(json_body)
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON body: {e}")
    _out(_put(base_url, f"/changes/{change_id}/revisions/{revision}/drafts",
              username, password, body))


def cmd_review(base_url: str, username: str, password: str, args: list[str]) -> None:
    """review <change-id> <revision> <json-body>"""
    if len(args) < 3:
        _die("Usage: review <change-id> <revision> <json-body>")
    change_id, revision, json_body = args[0], args[1], args[2]
    try:
        body = json.loads(json_body)
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON body: {e}")
    _out(_post(base_url, f"/changes/{change_id}/revisions/{revision}/review",
               username, password, body))


def cmd_submit(base_url: str, username: str, password: str, args: list[str]) -> None:
    """submit <change-id>"""
    if not args:
        _die("Usage: submit <change-id>")
    _out(_post(base_url, f"/changes/{args[0]}/submit", username, password, {}))


def cmd_abandon(base_url: str, username: str, password: str, args: list[str]) -> None:
    """abandon <change-id> [message]"""
    if not args:
        _die("Usage: abandon <change-id> [message]")
    body = {"message": args[1]} if len(args) > 1 else {}
    _out(_post(base_url, f"/changes/{args[0]}/abandon", username, password, body))


def cmd_restore(base_url: str, username: str, password: str, args: list[str]) -> None:
    """restore <change-id> [message]"""
    if not args:
        _die("Usage: restore <change-id> [message]")
    body = {"message": args[1]} if len(args) > 1 else {}
    _out(_post(base_url, f"/changes/{args[0]}/restore", username, password, body))


def cmd_add_reviewer(base_url: str, username: str, password: str, args: list[str]) -> None:
    """add-reviewer <change-id> <account-email-or-id>"""
    if len(args) < 2:
        _die("Usage: add-reviewer <change-id> <account-email-or-id>")
    body = {"reviewer": args[1]}
    _out(_post(base_url, f"/changes/{args[0]}/reviewers", username, password, body))


def cmd_set_topic(base_url: str, username: str, password: str, args: list[str]) -> None:
    """set-topic <change-id> <topic>"""
    if len(args) < 2:
        _die("Usage: set-topic <change-id> <topic>")
    body = {"topic": args[1]}
    _out(_put(base_url, f"/changes/{args[0]}/topic", username, password, body))


def cmd_help(*_) -> None:
    print(__doc__)


# ─── Dispatcher ───────────────────────────────────────────────────────────────

_COMMANDS = {
    "query":        cmd_query,
    "get-change":   cmd_get_change,
    "list-files":   cmd_list_files,
    "get-diff":     cmd_get_diff,
    "get-content":  cmd_get_content,
    "create-draft": cmd_create_draft,
    "review":       cmd_review,
    "submit":       cmd_submit,
    "abandon":      cmd_abandon,
    "restore":      cmd_restore,
    "add-reviewer": cmd_add_reviewer,
    "set-topic":    cmd_set_topic,
    "help":         cmd_help,
    "--help":       cmd_help,
    "-h":           cmd_help,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("help", "--help", "-h"):
        cmd_help()
        return

    command = sys.argv[1]
    args = sys.argv[2:]

    if command not in _COMMANDS:
        _die(f"Unknown command '{command}'. Run 'python gerrit_api.py help' for usage.")

    if command in ("help", "--help", "-h"):
        cmd_help()
        return

    base_url, username, password = load_config()
    _COMMANDS[command](base_url, username, password, args)


if __name__ == "__main__":
    main()
