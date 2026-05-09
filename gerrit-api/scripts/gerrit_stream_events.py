#!/usr/bin/env python3
"""
gerrit_stream_events.py — Listen to Gerrit SSH stream-events and parse them.

Connects to Gerrit via SSH, subscribes to the stream-events feed, and emits
parsed events as newline-delimited JSON to stdout (or a file).  Each output
line is a self-contained JSON object — ideal for shell pipelines, agent tools,
and log aggregators.

Usage:
  python3 gerrit_stream_events.py [options]

Options:
  --config FILE       Config file path (default: gerrit_config.json in cwd)
  --filter TYPE,...   Comma-separated event types to include (default: all)
                      e.g. patchset-created,change-merged,comment-added
  --project NAME,...  Comma-separated project names to filter (default: all)
  --branch NAME,...   Comma-separated branch names to filter (default: all)
  --output FILE       Append events to FILE in addition to stdout
  --max-events N      Stop after N events (default: 0 = unlimited)
  --timeout SECS      Stop after SECS seconds (default: 0 = unlimited)
  --reconnect         Reconnect on connection loss (default: exit on loss)
  --reconnect-delay N Seconds to wait before reconnecting (default: 5)
  --pretty            Pretty-print JSON output (human-readable)
  --summary           Emit a human-readable one-line summary per event
  --quiet             Suppress all log messages to stderr
  --help              Show this help

Credentials (config file keys / environment variables):
  ssh_host      / GERRIT_SSH_HOST      SSH hostname (extracted from url if absent)
  ssh_port      / GERRIT_SSH_PORT      SSH port (default: 29418)
  ssh_username  / GERRIT_SSH_USERNAME  SSH username (falls back to username)
  ssh_key       / GERRIT_SSH_KEY       Path to SSH private key (optional)

Event types emitted by Gerrit:
  patchset-created    A new patch set was uploaded
  change-merged       A change was merged/submitted
  change-abandoned    A change was abandoned
  change-restored     A change was restored
  comment-added       A comment or review vote was posted
  reviewer-added      A reviewer was added to a change
  reviewer-deleted    A reviewer was removed from a change
  topic-changed       A change topic was updated
  hashtags-changed    Change hashtags were updated
  vote-deleted        A review vote was deleted
  ref-updated         A git ref was updated (push/delete)
  project-created     A new project was created
  pending-check-updated  A pending check was updated

Examples:
  # Stream all events
  python3 gerrit_stream_events.py

  # Filter to patch uploads and merges, pretty-print
  python3 gerrit_stream_events.py --filter patchset-created,change-merged --pretty

  # Collect 20 events then exit
  python3 gerrit_stream_events.py --max-events 20

  # Run for 60 seconds, log to file, reconnect on drop
  python3 gerrit_stream_events.py --timeout 60 --output events.jsonl --reconnect

  # Show one-line summaries on stdout
  python3 gerrit_stream_events.py --summary

  # Pipe into jq for further filtering
  python3 gerrit_stream_events.py | jq 'select(.type == "patchset-created") | .summary'
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path


_SKILL_NAME = "gerrit-api"
_CONFIG_FILENAME = "gerrit_config.json"


# ─── Config loading ───────────────────────────────────────────────────────────

def _find_config_file(explicit_path: str | None) -> str | None:
    """Return the first config file found, searching in priority order.

    Priority:
      1. explicit_path (if --config was specified)
      2. {workspace}/config/{skill-name}/{filename}   ← preferred
      3. {workspace}/config/{filename}
      4. {workspace}/{filename}
      5. {skill-dir}/{filename}                       ← dev/testing fallback

    {workspace} = cwd when the script is invoked
    {skill-dir} = gerrit-api/ directory (parent of this scripts/ folder)
    """
    if explicit_path:
        return explicit_path if Path(explicit_path).is_file() else None

    workspace = Path.cwd()
    skill_dir = Path(__file__).parent.parent  # gerrit-api/

    candidates = [
        workspace / "config" / _SKILL_NAME / _CONFIG_FILENAME,
        workspace / "config" / _CONFIG_FILENAME,
        workspace / _CONFIG_FILENAME,
        skill_dir / _CONFIG_FILENAME,
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def _preferred_config_path() -> str:
    """Return the recommended path at which the user should create the config file."""
    return str(Path.cwd() / "config" / _SKILL_NAME / _CONFIG_FILENAME)

def load_config(config_path: str | None) -> dict:
    """Load credentials from config file (priority) then environment variables."""
    cfg: dict = {}

    found = _find_config_file(config_path)
    if found:
        try:
            with open(found) as f:
                cfg.update(json.load(f))
            _err(f"Using config: {found}")
        except (json.JSONDecodeError, OSError) as e:
            _err(f"Warning: could not read config file {found}: {e}")

    # 2. Environment variable fallbacks
    _env_fallback(cfg, "url",          "GERRIT_URL")
    _env_fallback(cfg, "username",     "GERRIT_USERNAME")
    _env_fallback(cfg, "password",     "GERRIT_HTTP_PASSWORD")
    _env_fallback(cfg, "ssh_host",     "GERRIT_SSH_HOST")
    _env_fallback(cfg, "ssh_port",     "GERRIT_SSH_PORT")
    _env_fallback(cfg, "ssh_username", "GERRIT_SSH_USERNAME")
    _env_fallback(cfg, "ssh_key",      "GERRIT_SSH_KEY")

    # Derive ssh_host from url when absent or empty (direct assignment also covers
    # the edge case where config file contained an explicit empty string "ssh_host":"")
    if not cfg.get("ssh_host") and cfg.get("url"):
        parsed = urllib.parse.urlparse(cfg["url"])
        cfg["ssh_host"] = parsed.hostname or ""

    # ssh_username falls back to http username (direct assignment for the same reason)
    if not cfg.get("ssh_username"):
        cfg["ssh_username"] = cfg.get("username", "")

    # Convert port to int
    raw_port = cfg.get("ssh_port", 29418)
    try:
        cfg["ssh_port"] = int(raw_port)
    except (TypeError, ValueError):
        cfg["ssh_port"] = 29418

    return cfg


def _env_fallback(cfg: dict, key: str, env_var: str) -> None:
    if not cfg.get(key):
        val = os.environ.get(env_var, "")
        if val:
            cfg[key] = val


# ─── SSH connection ───────────────────────────────────────────────────────────

def build_ssh_command(cfg: dict) -> list[str]:
    """Build the ssh command list for `gerrit stream-events`."""
    host = cfg.get("ssh_host", "")
    port = cfg.get("ssh_port", 29418)
    user = cfg.get("ssh_username", "")
    key  = cfg.get("ssh_key", "")

    if not host:
        preferred = _preferred_config_path()
        raise RuntimeError(
            "SSH host could not be determined.\n"
            "  Fix one of the following:\n"
            f'  1. Add "ssh_host": "gerrit.example.com" to {preferred}\n'
            '  2. Ensure "url" is set in the config file (ssh_host is derived from it)\n'
            "  3. Set environment variable: GERRIT_SSH_HOST=gerrit.example.com"
        )
    if not user:
        preferred = _preferred_config_path()
        raise RuntimeError(
            "SSH username could not be determined.\n"
            "  Fix one of the following:\n"
            f'  1. Add "ssh_username": "your-username" to {preferred}\n'
            '  2. Ensure "username" is set in the config file (ssh_username defaults to it)\n'
            "  3. Set environment variable: GERRIT_SSH_USERNAME=your-username"
        )

    cmd = [
        "ssh",
        "-p", str(port),
        # Disable strict host checking for automation; users may override via ~/.ssh/config
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        "-o", "ConnectTimeout=15",
    ]
    if key:
        key_path = str(Path(key).expanduser())
        cmd += ["-i", key_path]
    if user:
        cmd += ["-l", user]
    cmd += [host, "gerrit", "stream-events"]
    return cmd


# ─── Event parsing ────────────────────────────────────────────────────────────

def parse_event(raw_line: str) -> dict | None:
    """Parse a raw JSON line from `gerrit stream-events` into a dict.

    Returns None if the line is empty or not valid JSON.
    Adds a `_received_at` field with the local ISO timestamp.
    Adds a `summary` field with a human-readable one-line description.
    """
    line = raw_line.strip()
    if not line:
        return None
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None

    event["_received_at"] = datetime.now(timezone.utc).isoformat()
    event["summary"] = _summarize_event(event)
    return event


def _summarize_event(event: dict) -> str:
    """Return a short human-readable summary of a Gerrit event."""
    etype = event.get("type", "unknown")
    ts = _fmt_ts(event.get("eventCreatedOn"))

    # ── helpers ──
    def change_ref(change: dict) -> str:
        proj = change.get("project", "?")
        branch = change.get("branch", "?")
        num = change.get("number", "?")
        subject = change.get("subject", "")
        return f"[{proj}/{branch} #{num}] {subject!r}"

    def ps_ref(ps: dict) -> str:
        return f"ps{ps.get('number', '?')}"

    def actor(account: dict) -> str:
        return account.get("name") or account.get("username") or account.get("email") or "?"

    change = event.get("change", {})
    ps     = event.get("patchSet", {})

    if etype == "patchset-created":
        return (f"{ts} patchset-created: {actor(event.get('uploader', {}))} uploaded "
                f"{ps_ref(ps)} to {change_ref(change)}")

    if etype == "change-merged":
        return (f"{ts} change-merged: {actor(event.get('submitter', {}))} merged "
                f"{change_ref(change)} (rev {event.get('newRev','?')[:8]})")

    if etype == "change-abandoned":
        reason = event.get("reason", "")
        r = f" — {reason}" if reason else ""
        return (f"{ts} change-abandoned: {actor(event.get('abandoner', {}))} abandoned "
                f"{change_ref(change)}{r}")

    if etype == "change-restored":
        reason = event.get("reason", "")
        r = f" — {reason}" if reason else ""
        return (f"{ts} change-restored: {actor(event.get('restorer', {}))} restored "
                f"{change_ref(change)}{r}")

    if etype == "comment-added":
        approvals = event.get("approvals", [])
        votes = ", ".join(
            f"{a.get('type','?')}={a.get('value','?')}"
            for a in approvals
        )
        vote_str = f" [{votes}]" if votes else ""
        comment = event.get("comment", "")[:80]
        return (f"{ts} comment-added: {actor(event.get('author', {}))}{vote_str} on "
                f"{change_ref(change)} {ps_ref(ps)}: {comment!r}")

    if etype == "reviewer-added":
        return (f"{ts} reviewer-added: {actor(event.get('reviewer', {}))} added as reviewer on "
                f"{change_ref(change)}")

    if etype == "reviewer-deleted":
        return (f"{ts} reviewer-deleted: {actor(event.get('reviewer', {}))} removed from "
                f"{change_ref(change)}")

    if etype == "vote-deleted":
        approvals = event.get("approvals", [])
        votes = ", ".join(
            f"{a.get('type','?')}={a.get('value','?')}"
            for a in approvals
        )
        return (f"{ts} vote-deleted: {actor(event.get('remover', {}))} deleted vote(s) [{votes}] "
                f"by {actor(event.get('reviewer', {}))} on {change_ref(change)}")

    if etype == "topic-changed":
        old = event.get("oldTopic", "")
        new = change.get("topic", "")
        return (f"{ts} topic-changed: {actor(event.get('changer', {}))} changed topic "
                f"{old!r} → {new!r} on {change_ref(change)}")

    if etype == "hashtags-changed":
        added   = event.get("added", [])
        removed = event.get("removed", [])
        parts = []
        if added:   parts.append(f"added {added}")
        if removed: parts.append(f"removed {removed}")
        return (f"{ts} hashtags-changed: {actor(event.get('editor', {}))} {', '.join(parts)} "
                f"on {change_ref(change)}")

    if etype == "ref-updated":
        ref_upd = event.get("refUpdate", {})
        proj    = ref_upd.get("project", "?")
        ref     = ref_upd.get("refName", "?")
        old_rev = ref_upd.get("oldRev", "?" * 40)[:8]
        new_rev = ref_upd.get("newRev", "?" * 40)[:8]
        return (f"{ts} ref-updated: {proj} {ref} {old_rev}..{new_rev} "
                f"by {actor(event.get('submitter', {}))}")

    if etype == "project-created":
        return (f"{ts} project-created: {event.get('projectName','?')} "
                f"(head: {event.get('headName','?')})")

    if etype == "pending-check-updated":
        check = event.get("pendingChecksInfo", {})
        return (f"{ts} pending-check-updated: {change_ref(change)} "
                f"checkers={list(check.get('pendingChecks', {}).keys())}")

    # Generic fallback
    return f"{ts} {etype}: {json.dumps(event, separators=(',', ':'))[:200]}"


def _fmt_ts(epoch: int | float | None) -> str:
    if epoch is None:
        return ""
    try:
        return datetime.fromtimestamp(float(epoch), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, OSError):
        return ""


# ─── Filtering ────────────────────────────────────────────────────────────────

def matches_filters(
    event: dict,
    type_filter: set[str],
    project_filter: set[str],
    branch_filter: set[str],
) -> bool:
    if type_filter and event.get("type") not in type_filter:
        return False
    change = event.get("change", {})
    ref_upd = event.get("refUpdate", {})
    if project_filter:
        proj = change.get("project") or ref_upd.get("project") or event.get("projectName", "")
        if proj not in project_filter:
            return False
    if branch_filter:
        branch = change.get("branch") or ref_upd.get("refName", "")
        if branch not in branch_filter:
            return False
    return True


# ─── Output ───────────────────────────────────────────────────────────────────

def emit_event(event: dict, out_file, pretty: bool, show_summary: bool) -> None:
    if show_summary:
        line = event["summary"]
    elif pretty:
        line = json.dumps(event, indent=2, ensure_ascii=False)
    else:
        line = json.dumps(event, separators=(",", ":"), ensure_ascii=False)

    print(line, flush=True)
    if out_file:
        # Always write compact JSON to file regardless of display mode
        out_file.write(
            json.dumps(event, separators=(",", ":"), ensure_ascii=False) + "\n"
        )
        out_file.flush()


# ─── Stream loop ─────────────────────────────────────────────────────────────

def _err(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def stream_events(args: argparse.Namespace) -> int:
    """Main event streaming loop. Returns exit code."""
    cfg = load_config(args.config)

    type_filter    = set(f.strip() for f in args.filter.split(",") if f.strip()) if args.filter else set()
    project_filter = set(p.strip() for p in args.project.split(",") if p.strip()) if args.project else set()
    branch_filter  = set(b.strip() for b in args.branch.split(",") if b.strip()) if args.branch else set()

    try:
        ssh_cmd = build_ssh_command(cfg)
    except RuntimeError as e:
        _err(f"ERROR: {e}")
        return 1

    if not args.quiet:
        host = cfg.get("ssh_host", "?")
        port = cfg.get("ssh_port", 29418)
        user = cfg.get("ssh_username", "?")
        _err(f"Connecting to {user}@{host}:{port} …")
        if type_filter:
            _err(f"Filtering event types: {sorted(type_filter)}")
        if project_filter:
            _err(f"Filtering projects: {sorted(project_filter)}")
        if branch_filter:
            _err(f"Filtering branches: {sorted(branch_filter)}")

    deadline = time.monotonic() + args.timeout if args.timeout > 0 else None
    max_events = args.max_events
    reconnect_delay = args.reconnect_delay

    # Set up graceful shutdown on SIGINT / SIGTERM
    _stop = [False]
    def _handle_signal(sig, frame):
        _stop[0] = True
    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    out_file = None
    if args.output:
        out_file = open(args.output, "a", encoding="utf-8")

    event_count = 0
    exit_code = 0

    try:
        while not _stop[0]:
            # Check deadline before each (re)connect
            if deadline and time.monotonic() >= deadline:
                if not args.quiet:
                    _err("Timeout reached, exiting.")
                break

            proc = None
            try:
                proc = subprocess.Popen(
                    ssh_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )

                if not args.quiet:
                    _err(f"Connected. Listening for events (PID {proc.pid}) …")

                for raw_line in proc.stdout:  # type: ignore[union-attr]
                    if _stop[0]:
                        break
                    if deadline and time.monotonic() >= deadline:
                        _stop[0] = True
                        break

                    event = parse_event(raw_line)
                    if event is None:
                        continue
                    if not matches_filters(event, type_filter, project_filter, branch_filter):
                        continue

                    emit_event(event, out_file, args.pretty, args.summary)
                    event_count += 1

                    if max_events > 0 and event_count >= max_events:
                        if not args.quiet:
                            _err(f"Reached max-events={max_events}, exiting.")
                        _stop[0] = True
                        break

                proc.wait()
                stderr_output = proc.stderr.read().strip() if proc.stderr else ""

                if _stop[0]:
                    break

                if proc.returncode != 0:
                    if not args.quiet:
                        _err(f"SSH process exited with code {proc.returncode}.")
                        if stderr_output:
                            _err(f"SSH stderr: {stderr_output}")
                        # Targeted guidance based on error type
                        stderr_lc = stderr_output.lower()
                        ssh_key_info = cfg.get("ssh_key") or "(default keys from ~/.ssh/)"
                        if "permission denied" in stderr_lc or "publickey" in stderr_lc:
                            _err(f"  → Auth failed. SSH user: {cfg.get('ssh_username')!r}, "
                                 f"key: {ssh_key_info}")
                            _err("  → Ensure your SSH public key is uploaded to Gerrit:")
                            _err("    Gerrit web UI → Settings → SSH Keys → Add Key")
                        elif ("connection refused" in stderr_lc
                              or "connect to host" in stderr_lc
                              or "no route to host" in stderr_lc):
                            _err(f"  → Cannot connect to {cfg.get('ssh_host')!r} "
                                 f"port {cfg.get('ssh_port')}.")
                            _err("  → Check ssh_host and ssh_port in gerrit_config.json.")
                            _err(f"  → Test: ssh -p {cfg.get('ssh_port')} "
                                 f"{cfg.get('ssh_username')}@{cfg.get('ssh_host')} gerrit version")
                        elif "not allowed" in stderr_lc or "access denied" in stderr_lc:
                            _err("  → This Gerrit account may lack 'Stream Events' capability.")
                            _err("    Ask a Gerrit admin to grant it under Global Capabilities.")
                        else:
                            _err(f"  → Verify gerrit_config.json: "
                                 f"ssh_host={cfg.get('ssh_host')!r}, "
                                 f"ssh_port={cfg.get('ssh_port')}, "
                                 f"ssh_username={cfg.get('ssh_username')!r}")
                            _err(f"  → Test: ssh -p {cfg.get('ssh_port')} "
                                 f"{cfg.get('ssh_username')}@{cfg.get('ssh_host')} gerrit version")
                    if not args.reconnect:
                        exit_code = proc.returncode or 1
                        break
                else:
                    if not args.quiet:
                        _err("SSH connection closed normally.")
                    if not args.reconnect:
                        break

            except OSError as e:
                if not args.quiet:
                    _err(f"SSH launch error: {e}")
                    if "No such file" in str(e) or "not found" in str(e).lower():
                        _err("  → 'ssh' is not installed or not in PATH. Install OpenSSH.")
                    else:
                        _err(f"  → Verify: ssh_host={cfg.get('ssh_host')!r}, "
                             f"ssh_port={cfg.get('ssh_port')}, "
                             f"ssh_username={cfg.get('ssh_username')!r}")
                if not args.reconnect:
                    exit_code = 1
                    break
            finally:
                if proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()

            if args.reconnect and not _stop[0]:
                if not args.quiet:
                    _err(f"Reconnecting in {reconnect_delay}s …")
                for _ in range(reconnect_delay * 10):
                    if _stop[0]:
                        break
                    time.sleep(0.1)

    finally:
        if out_file:
            out_file.close()
        if not args.quiet:
            _err(f"Done. Total events emitted: {event_count}")

    return exit_code


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gerrit_stream_events.py",
        description="Listen to Gerrit SSH stream-events and emit parsed JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        add_help=False,
    )
    parser.add_argument("--config",          metavar="FILE",   default=None,
                        help="Config file (default: gerrit_config.json in cwd)")
    parser.add_argument("--filter",          metavar="TYPES",  default="",
                        help="Comma-separated event types to include (default: all)")
    parser.add_argument("--project",         metavar="NAMES",  default="",
                        help="Comma-separated project names to filter")
    parser.add_argument("--branch",          metavar="NAMES",  default="",
                        help="Comma-separated branch names to filter")
    parser.add_argument("--output",          metavar="FILE",   default="",
                        help="Append events to FILE (compact JSON) in addition to stdout")
    parser.add_argument("--max-events",      metavar="N",      type=int, default=0,
                        help="Stop after N events (0 = unlimited)")
    parser.add_argument("--timeout",         metavar="SECS",   type=int, default=0,
                        help="Stop after SECS seconds (0 = unlimited)")
    parser.add_argument("--reconnect",       action="store_true",
                        help="Reconnect on connection loss")
    parser.add_argument("--reconnect-delay", metavar="N",      type=int, default=5,
                        help="Seconds to wait before reconnecting (default: 5)")
    parser.add_argument("--pretty",          action="store_true",
                        help="Pretty-print JSON output")
    parser.add_argument("--summary",         action="store_true",
                        help="Emit one-line human-readable summaries instead of JSON")
    parser.add_argument("--quiet",           action="store_true",
                        help="Suppress log messages to stderr")
    parser.add_argument("--help", "-h",      action="help",
                        help="Show this help and exit")

    args = parser.parse_args()
    sys.exit(stream_events(args))


if __name__ == "__main__":
    main()
