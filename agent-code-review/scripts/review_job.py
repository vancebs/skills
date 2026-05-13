#!/usr/bin/env python3
"""
review_job.py — Gerrit Code Review Preparation Job

Run by a cron job (typically every 1 minute). Does all machine-executable work:
  1. Ensures the Gerrit stream-events SSH listener process is running (starts it if dead)
  2. Reads pending patchset-created events from the queue file
  3. Fetches commit message and file diffs via Gerrit REST API
  4. Outputs structured JSON to stdout for the LLM agent to review

After this script exits, the LLM agent:
  - Reads the JSON output
  - Performs code review for each event using T2MCodingRule
  - Calls post_result.py to submit the review (or display it in test_mode)

Usage:
    python3 "$SKILL_DIR/scripts/review_job.py" --workspace "$SKILL_WORKSPACE"

Exit codes:
    0 — OK (JSON output written to stdout)
    1 — Fatal error (config missing, cannot continue)
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from base64 import b64encode
from datetime import datetime, timezone

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


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _find_config(ws, override=None):
    if override:
        p = Path(override)
        return p if p.is_file() else None
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
            return p
    return None


def _load_config(ws, override=None):
    p = _find_config(ws, override)
    if not p:
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# SSH stream listener management
# ---------------------------------------------------------------------------

def _build_ssh_cmd(cfg):
    """Return the SSH command list for gerrit stream-events."""
    from urllib.parse import urlparse
    url      = cfg.get("url", "")
    parsed   = urlparse(url)
    ssh_host = cfg.get("ssh_host", "").strip() or parsed.hostname or ""
    ssh_port = int(cfg.get("ssh_port", 29418))
    ssh_user = cfg.get("ssh_username", "").strip() or cfg.get("username", "").strip()
    ssh_key  = cfg.get("ssh_key", "").strip()

    cmd = [
        "ssh", "-p", str(ssh_port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=15",
    ]
    if ssh_key:
        cmd += ["-i", str(Path(ssh_key).expanduser())]
    cmd += [f"{ssh_user}@{ssh_host}", "gerrit", "stream-events"]
    return cmd


def _listener_alive(pid_file):
    """Return True if the listener process recorded in pid_file is still alive."""
    p = Path(pid_file)
    if not p.exists():
        return False
    try:
        pid = int(p.read_text().strip())
        os.kill(pid, 0)   # signal 0 = check existence without sending a signal
        return True
    except (ValueError, ProcessLookupError, PermissionError, OSError):
        return False


def _start_listener(cfg, events_file, pid_file):
    """
    Start the SSH stream-events listener as a detached background process.
    The process writes Gerrit event JSON lines directly to events_file.
    Returns (pid, error_message).  error_message is None on success.
    """
    events_path = Path(events_file)
    events_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = _build_ssh_cmd(cfg)

    # Open events file in append+binary mode.
    # The child process inherits this file descriptor and keeps writing after the
    # parent closes its copy — standard POSIX file descriptor inheritance.
    fout = open(events_path, "ab")
    ferr = open(os.devnull, "wb")
    try:
        if sys.platform == "win32":
            proc = subprocess.Popen(
                cmd, stdout=fout, stderr=ferr,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            proc = subprocess.Popen(
                cmd, stdout=fout, stderr=ferr,
                start_new_session=True,    # detach from parent session (setsid equivalent)
            )
        pid_path = Path(pid_file)
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(str(proc.pid))
        return proc.pid, None
    except FileNotFoundError:
        return None, "ssh command not found — install OpenSSH client"
    except Exception as e:
        return None, str(e)
    finally:
        fout.close()
        ferr.close()


# ---------------------------------------------------------------------------
# Event queue reading (cursor-based, no locking required)
# ---------------------------------------------------------------------------

def _read_new_events(events_file, cursor_file):
    """
    Read events appended since the last call (using a cursor/bookmark file).
    Only returns complete JSON lines (partial last line is left for next call).
    Safe for concurrent SSH writer + this reader (single-consumer, cursor-based).
    """
    events_path = Path(events_file)
    cursor_path = Path(cursor_file)

    pos = 0
    if cursor_path.exists():
        try:
            pos = int(cursor_path.read_text().strip())
        except Exception:
            pos = 0

    if not events_path.exists():
        return []

    try:
        with open(events_path, "rb") as f:
            size = f.seek(0, 2)         # file size
            if pos > size:
                pos = 0                 # file was replaced/truncated
            f.seek(pos)
            data = f.read()
    except Exception:
        return []

    if not data:
        return []

    # Process only complete lines (skip the last partial line if any)
    if data[-1:] != b"\n":
        last_nl = data.rfind(b"\n")
        if last_nl < 0:
            return []                   # no complete lines yet
        complete = data[: last_nl + 1]
        new_pos  = pos + last_nl + 1
    else:
        complete = data
        new_pos  = pos + len(data)

    events = []
    for line in complete.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # skip malformed lines

    # Update cursor
    cursor_path.parent.mkdir(parents=True, exist_ok=True)
    cursor_path.write_text(str(new_pos))
    return events


# ---------------------------------------------------------------------------
# Gerrit REST API helpers
# ---------------------------------------------------------------------------

def _gerrit_get(cfg, path):
    """Authenticated GET to Gerrit REST API. Returns (data, error_str)."""
    url      = cfg.get("url", "").rstrip("/")
    username = cfg.get("username", "")
    password = cfg.get("password", "")
    creds    = b64encode(f"{username}:{password}".encode()).decode()

    req = Request(
        f"{url}{path}",
        headers={"Authorization": f"Basic {creds}", "Accept": "application/json"},
    )
    try:
        with urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            if body.startswith(")]}'"):
                body = body[5:]          # strip Gerrit XSSI prefix
            return json.loads(body), None
    except HTTPError as e:
        return None, f"HTTP {e.code}"
    except URLError as e:
        return None, f"Connection error: {e.reason}"
    except Exception as e:
        return None, str(e)


def _url_encode(s):
    from urllib.parse import quote
    return quote(str(s), safe="")


def _fetch_commit_message(cfg, change_number, revision):
    data, err = _gerrit_get(cfg, f"/a/changes/{change_number}/revisions/{revision}/commit")
    if err or not isinstance(data, dict):
        return ""
    return data.get("message", "")


def _fetch_files(cfg, change_number, revision):
    """Returns dict of {path: file_info} or {}."""
    data, err = _gerrit_get(cfg, f"/a/changes/{change_number}/revisions/{revision}/files/")
    if err or not isinstance(data, dict):
        return {}, err
    return data, None


def _fetch_diff(cfg, change_number, revision, file_path):
    """Returns unified-style diff text or None on error."""
    enc  = _url_encode(file_path)
    data, err = _gerrit_get(
        cfg,
        f"/a/changes/{change_number}/revisions/{revision}/files/{enc}/diff",
    )
    if err or not isinstance(data, dict):
        return None

    lines   = []
    content = data.get("content", [])
    for chunk in content:
        for line in chunk.get("ab", []):   # unchanged
            lines.append(f"  {line}")
        for line in chunk.get("a", []):    # removed
            lines.append(f"- {line}")
        for line in chunk.get("b", []):    # added
            lines.append(f"+ {line}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Event processing
# ---------------------------------------------------------------------------

def _filter_events(events, cfg):
    """Keep only patchset-created events that match configured project/branch filters."""
    projects = [p.strip() for p in cfg.get("review_projects", []) if p.strip()]
    branches = [b.strip() for b in cfg.get("review_branches", []) if b.strip()]

    result = []
    for ev in events:
        if ev.get("type") != "patchset-created":
            continue
        change = ev.get("change", {})
        if projects and change.get("project", "") not in projects:
            continue
        if branches and change.get("branch", "") not in branches:
            continue
        result.append(ev)
    return result


def _process_event(cfg, event, skip_patterns=None):
    """
    Fetch all data needed for code review for a single patchset-created event.
    Returns a dict ready for LLM consumption.
    """
    import fnmatch
    change   = event.get("change", {})
    patchset = event.get("patchSet", {})

    change_number  = str(change.get("number") or change.get("id", ""))
    revision       = patchset.get("revision", "current")
    patchset_num   = patchset.get("number", 1)

    entry = {
        "change_id":       change_number,
        "patchset_number": patchset_num,
        "project":         change.get("project", ""),
        "branch":          change.get("branch", ""),
        "subject":         change.get("subject", ""),
        "uploader":        (event.get("uploader") or {}).get("username", ""),
        "revision":        revision,
        "received_at":     event.get("_received_at",
                                     datetime.now(timezone.utc).isoformat()),
    }

    # Commit message
    entry["commit_message"] = _fetch_commit_message(cfg, change_number, revision)

    # Files and diffs
    files_data, err = _fetch_files(cfg, change_number, revision)
    if err:
        entry["error"] = f"Failed to fetch files: {err}"
        entry["files"] = []
        return entry

    status_map = {"A": "ADDED", "D": "DELETED", "M": "MODIFIED",
                  "R": "RENAMED", "C": "COPIED"}
    files = []
    for file_path, file_info in files_data.items():
        if file_path == "/COMMIT_MSG":
            continue  # skip Gerrit's synthetic commit-message file

        # Apply skip patterns
        if skip_patterns:
            basename = os.path.basename(file_path)
            if any(fnmatch.fnmatch(file_path, p) or fnmatch.fnmatch(basename, p)
                   for p in skip_patterns):
                continue

        status = status_map.get(file_info.get("status", "M"), "MODIFIED")
        fentry = {"path": file_path, "status": status}

        if status != "DELETED":
            diff = _fetch_diff(cfg, change_number, revision, file_path)
            fentry["diff"] = diff if diff is not None else "(diff unavailable)"
        else:
            fentry["diff"] = "(file deleted)"

        files.append(fentry)

    entry["files"] = files
    return entry


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Gerrit Code Review Preparation Job — run by cron every ~1 min")
    parser.add_argument("--workspace",   help="Project workspace directory (overrides SKILL_WORKSPACE)")
    parser.add_argument("--config",      help="Config file path")
    parser.add_argument("--events-file", help="Events queue file path (overrides config)")
    parser.add_argument("--no-diffs",    action="store_true",
                        help="Skip fetching diffs (faster, for testing)")
    parser.add_argument("--dry-run",     action="store_true",
                        help="List events without advancing the cursor")
    args = parser.parse_args()

    ws = _workspace(args)

    # Load config
    cfg = _load_config(ws, args.config)
    if not cfg:
        result = {
            "status":        "error",
            "error":         "配置文件未找到。请运行 check_env.py 检查环境并创建配置文件。",
            "events_count":  0,
            "events":        [],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    test_mode     = cfg.get("test_mode", True)
    skip_patterns = cfg.get("skip_file_patterns", [])

    # Derived file paths
    events_file = (args.events_file
                   or (cfg.get("events_file") or "").strip()
                   or str(ws / "events.jsonl"))
    pid_file    = str(ws / "gerrit_listener.pid")
    cursor_file = str(ws / "events.cursor")

    # ── Phase 1: Ensure SSH listener is running ─────────────────────────────
    listener_status = "running"
    if not _listener_alive(pid_file):
        pid, err = _start_listener(cfg, events_file, pid_file)
        if err:
            listener_status = f"start_failed: {err}"
        else:
            listener_status = "started"
            time.sleep(2)           # brief pause so listener can connect

    # ── Phase 2: Read pending events ────────────────────────────────────────
    cursor = cursor_file if not args.dry_run else cursor_file + ".dry"
    raw_events = _read_new_events(events_file, cursor)
    relevant   = _filter_events(raw_events, cfg)

    # ── Phase 3: Fetch diffs ────────────────────────────────────────────────
    processed = []
    for ev in relevant:
        if args.no_diffs:
            change = ev.get("change", {})
            processed.append({
                "change_id": str(change.get("number", "")),
                "project":   change.get("project", ""),
                "branch":    change.get("branch", ""),
                "subject":   change.get("subject", ""),
            })
        else:
            processed.append(_process_event(cfg, ev, skip_patterns))

    # ── Output ──────────────────────────────────────────────────────────────
    output = {
        "status":          "ok",
        "test_mode":       test_mode,
        "listener_status": listener_status,
        "events_count":    len(processed),
        "events":          processed,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
