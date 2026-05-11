#!/usr/bin/env python3
"""
gerrit_stream_events.py — Listen to Gerrit SSH stream-events and parse them.

Connects to Gerrit via SSH, subscribes to the stream-events feed, and delivers
parsed events to stdout, an append-only JSONL file, and/or an HTTP hook
endpoint.  Each event line is a self-contained JSON object enriched with
_received_at and summary fields.

Usage:
  python3 gerrit_stream_events.py [options]

─── File output ──────────────────────────────────────────────────────────────
  --output PATH         Append events to PATH as compact JSONL (one event per
                        line). Omit or leave empty to skip file output.
  --no-output           Explicitly disable file output.
  --atomic-write        Atomic append + fsync on every write (default: on).
  --no-atomic-write     Disable atomic writes (compat mode; not recommended).

─── HTTP hook ────────────────────────────────────────────────────────────────
  --hook-url URL        POST each event as JSON to this URL.
                        Example: --hook-url http://127.0.0.1:8443/events
  --hook-token TOKEN    Sent as X-Auth-Token header. Never logged. Can also be
                        set via config key hook_token or env HOOK_TOKEN.
  --hook-retries N      Max retries on 5xx/network error (default: 3).
  --hook-timeout SECS   Per-request timeout in seconds (default: 3).
  --outbox PATH         On hook failure, append missed events here for later
                        replay. Default: <workspace>/events.outbox.jsonl.

─── Daemon / process ─────────────────────────────────────────────────────────
  --pid-file PATH       Write PID to PATH on startup; remove on clean exit.
  --dry-run             Parse and print events; skip all file writes and hooks.

─── Filtering ────────────────────────────────────────────────────────────────
  --filter TYPE,...     Comma-separated event types (default: all).
  --project NAME,...    Comma-separated project names to include.
  --branch NAME,...     Comma-separated branch names to include.

─── Stream control ───────────────────────────────────────────────────────────
  --max-events N        Stop after N events (0 = unlimited).
  --timeout SECS        Stop after SECS seconds (0 = unlimited).
  --reconnect           Reconnect on connection loss (exponential backoff).
  --reconnect-delay N   Initial reconnect delay in seconds (default: 5).

─── Display ──────────────────────────────────────────────────────────────────
  --pretty              Pretty-print JSON output to stdout.
  --summary             Emit one-line human-readable summary per event.
  --verbose             Enable DEBUG-level logging to stderr.
  --quiet               Suppress all log output.

─── Misc ─────────────────────────────────────────────────────────────────────
  --config FILE         Config file path (searches 7 default locations).
  --help                Show this help.

Credentials (config file keys / env vars / CLI override priority: CLI > config > env):
  ssh_host      / GERRIT_SSH_HOST      SSH hostname (derived from url if absent)
  ssh_port      / GERRIT_SSH_PORT      SSH port (default: 29418)
  ssh_username  / GERRIT_SSH_USERNAME  SSH username (falls back to username)
  ssh_key       / GERRIT_SSH_KEY       Path to SSH private key (optional)
  hook_url      / HOOK_URL             HTTP hook URL
  hook_token    / HOOK_TOKEN           HTTP hook token (never logged)
  outbox_path   / OUTBOX_PATH          Outbox file path

Event types emitted by Gerrit:
  patchset-created       A new patch set was uploaded
  change-merged          A change was merged/submitted
  change-abandoned       A change was abandoned
  change-restored        A change was restored
  comment-added          A comment or review vote was posted
  reviewer-added         A reviewer was added to a change
  reviewer-deleted       A reviewer was removed from a change
  topic-changed          A change topic was updated
  hashtags-changed       Change hashtags were updated
  vote-deleted           A review vote was deleted
  ref-updated            A git ref was updated (push/delete)
  project-created        A new project was created
  pending-check-updated  A pending check was updated

Examples:
  # Stream all events
  python3 gerrit_stream_events.py

  # Filter to patch uploads and merges, pretty-print
  python3 gerrit_stream_events.py --filter patchset-created,change-merged --pretty

  # Write to file + push to hook, auto-reconnect (systemd / foreground)
  python3 gerrit_stream_events.py \\
    --output /var/log/gerrit/events.jsonl \\
    --hook-url http://127.0.0.1:8443/events \\
    --hook-token MY_TOKEN --reconnect

  # Only hook, no file (outbox protects against delivery failures)
  python3 gerrit_stream_events.py \\
    --no-output --hook-url http://127.0.0.1:8443/events \\
    --hook-token MY_TOKEN --reconnect

  # Dry-run: show summaries, no writes
  python3 gerrit_stream_events.py --dry-run --summary
"""

import argparse
import json
import logging
import os
import random
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Module-level logger — configured in _setup_logging() before first use.
log = logging.getLogger("gerrit_stream_events")


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
      6. $HOME/.config/{skill-name}/{filename}
      7. $HOME/.config/{filename}
      8. $HOME/{filename}

    {workspace} = cwd when the script is invoked
    {skill-dir} = gerrit-api/ directory (parent of this scripts/ folder)
    """
    if explicit_path:
        return explicit_path if Path(explicit_path).is_file() else None

    workspace = Path.cwd()
    skill_dir = Path(__file__).parent.parent  # gerrit-api/
    home = Path.home()

    candidates = [
        workspace / "config" / _SKILL_NAME / _CONFIG_FILENAME,
        workspace / "config" / _CONFIG_FILENAME,
        workspace / _CONFIG_FILENAME,
        skill_dir / _CONFIG_FILENAME,
        home / ".config" / _SKILL_NAME / _CONFIG_FILENAME,
        home / ".config" / _CONFIG_FILENAME,
        home / _CONFIG_FILENAME,
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
            log.info("Using config: %s", found)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Could not read config file %s: %s", found, e)

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


# ─── Logging setup ────────────────────────────────────────────────────────────

def _setup_logging(verbose: bool, quiet: bool) -> None:
    """Configure the module logger based on verbosity flags."""
    if quiet:
        log.setLevel(logging.CRITICAL)
    elif verbose:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
    if not log.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        log.addHandler(handler)


# ─── Atomic file write ────────────────────────────────────────────────────────

def _atomic_append(path: str, data: bytes) -> None:
    """Append *data* to *path* atomically using O_APPEND + fsync.

    On POSIX systems, O_APPEND guarantees that concurrent writers cannot
    interleave partial lines (kernel atomicity for writes ≤ PIPE_BUF).
    fsync ensures data hits disk before this function returns.
    On Windows, we use binary mode open + flush (best effort).
    """
    if os.name == "nt":  # Windows
        with open(path, "ab") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    else:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)


def write_event_to_file(path: str, event: dict, atomic: bool) -> None:
    """Serialise *event* as a JSONL line and append it to *path*."""
    line = json.dumps(event, separators=(",", ":"), ensure_ascii=False) + "\n"
    data = line.encode("utf-8")
    try:
        if atomic:
            _atomic_append(path, data)
        else:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
        log.debug("Wrote event to %s (len=%d)", path, len(data))
    except OSError as e:
        log.error("Failed to write event to %s: %s", path, e)


# ─── HTTP hook delivery ───────────────────────────────────────────────────────

def send_event_to_hook(
    event: dict,
    url: str,
    token: str | None,
    retries: int,
    timeout: float,
    outbox: str | None,
    atomic: bool,
) -> None:
    """POST *event* to *url*, retrying on 5xx/network errors.

    Retry strategy: exponential back-off starting at 0.5 s, doubling each
    attempt, with ±10 % jitter.  4xx responses are not retried.
    After all retries are exhausted the event is written to *outbox*.
    The hook token is never written to logs.
    """
    body = json.dumps(event, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Auth-Token"] = token

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    last_error = "unknown error"

    for attempt in range(retries + 1):
        if attempt > 0:
            base_delay = 0.5 * (2 ** (attempt - 1))
            delay = base_delay * (1.0 + random.uniform(-0.1, 0.1))
            log.warning("Hook POST failed %s; retrying (%d/%d) in %.1fs",
                        last_error, attempt, retries, delay)
            time.sleep(delay)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                if 200 <= status < 300:
                    log.debug("Hook POST succeeded (HTTP %d)", status)
                    return
                if 400 <= status < 500:
                    log.error("Hook POST client error HTTP %d; not retrying", status)
                    return
                last_error = f"HTTP {status}"
        except urllib.error.HTTPError as exc:
            if 400 <= exc.code < 500:
                log.error("Hook POST client error HTTP %d; not retrying", exc.code)
                return
            last_error = f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001
            last_error = type(exc).__name__

    log.error("Hook failed after %d retries (%s); appended to outbox", retries, last_error)
    if outbox:
        try:
            data = json.dumps(event, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
            if atomic:
                _atomic_append(outbox, data)
            else:
                with open(outbox, "ab") as f:
                    f.write(data)
        except OSError as exc:
            log.error("Failed to write to outbox %s: %s", outbox, exc)


# ─── SSH error guidance ───────────────────────────────────────────────────────

def _log_ssh_error(stderr_output: str, cfg: dict) -> None:
    """Log targeted SSH error guidance without leaking secrets."""
    stderr_lc = stderr_output.lower()
    ssh_key_info = cfg.get("ssh_key") or "(default keys from ~/.ssh/)"
    if "permission denied" in stderr_lc or "publickey" in stderr_lc:
        log.error("Auth failed. SSH user: %r, key: %s", cfg.get("ssh_username"), ssh_key_info)
        log.error("Ensure your SSH public key is uploaded to Gerrit:")
        log.error("  Gerrit web UI → Settings → SSH Keys → Add Key")
    elif ("connection refused" in stderr_lc
          or "connect to host" in stderr_lc
          or "no route to host" in stderr_lc):
        log.error("Cannot connect to %r port %s.", cfg.get("ssh_host"), cfg.get("ssh_port"))
        log.error("Check ssh_host and ssh_port in gerrit_config.json.")
        log.error("Test: ssh -p %s %s@%s gerrit version",
                  cfg.get("ssh_port"), cfg.get("ssh_username"), cfg.get("ssh_host"))
    elif "not allowed" in stderr_lc or "access denied" in stderr_lc:
        log.error("This Gerrit account may lack 'Stream Events' capability.")
        log.error("Ask a Gerrit admin to grant it under Global Capabilities.")
    else:
        log.warning("Verify gerrit_config.json: ssh_host=%r, ssh_port=%s, ssh_username=%r",
                    cfg.get("ssh_host"), cfg.get("ssh_port"), cfg.get("ssh_username"))
        log.warning("Test: ssh -p %s %s@%s gerrit version",
                    cfg.get("ssh_port"), cfg.get("ssh_username"), cfg.get("ssh_host"))


# ─── Output ───────────────────────────────────────────────────────────────────

def emit_event(event: dict, pretty: bool, show_summary: bool) -> None:
    """Print event to stdout."""
    if show_summary:
        print(event["summary"], flush=True)
    elif pretty:
        print(json.dumps(event, indent=2, ensure_ascii=False), flush=True)
    else:
        print(json.dumps(event, separators=(",", ":"), ensure_ascii=False), flush=True)


def stream_events(args: argparse.Namespace) -> int:
    """Main event streaming loop. Returns exit code."""
    _setup_logging(getattr(args, "verbose", False), args.quiet)
    cfg = load_config(args.config)

    type_filter    = set(f.strip() for f in args.filter.split(",")  if f.strip()) if args.filter  else set()
    project_filter = set(p.strip() for p in args.project.split(",") if p.strip()) if args.project else set()
    branch_filter  = set(b.strip() for b in args.branch.split(",")  if b.strip()) if args.branch  else set()

    try:
        ssh_cmd = build_ssh_command(cfg)
    except RuntimeError as exc:
        log.error("%s", exc)
        return 1

    log.info("Connecting to %s@%s:%s …",
             cfg.get("ssh_username"), cfg.get("ssh_host"), cfg.get("ssh_port"))
    if type_filter:
        log.info("Filtering event types: %s", sorted(type_filter))
    if project_filter:
        log.info("Filtering projects: %s", sorted(project_filter))
    if branch_filter:
        log.info("Filtering branches: %s", sorted(branch_filter))

    # ── Resolve output path ──────────────────────────────────────────────────
    output_path: str | None = None
    if not getattr(args, "no_output", False) and args.output:
        output_path = args.output

    # ── Resolve hook settings (CLI > config > env) ───────────────────────────
    hook_url   = args.hook_url   or cfg.get("hook_url")   or os.environ.get("HOOK_URL",   "")
    hook_token = args.hook_token or cfg.get("hook_token") or os.environ.get("HOOK_TOKEN", "")

    # ── Resolve outbox path ──────────────────────────────────────────────────
    outbox_path: str | None = (
        args.outbox
        or cfg.get("outbox_path")
        or os.environ.get("OUTBOX_PATH", "")
        or (str(Path.cwd() / "events.outbox.jsonl") if hook_url else None)
    ) or None

    if args.dry_run:
        log.info("DRY RUN mode: events will be parsed and printed, but not written or POSTed")

    # ── PID file ─────────────────────────────────────────────────────────────
    pid_file_path: str | None = None
    if getattr(args, "pid_file", ""):
        try:
            Path(args.pid_file).write_text(str(os.getpid()), encoding="utf-8")
            log.debug("PID %d written to %s", os.getpid(), args.pid_file)
            pid_file_path = args.pid_file
        except OSError as exc:
            log.warning("Could not write PID file %s: %s", args.pid_file, exc)

    deadline = time.monotonic() + args.timeout if args.timeout > 0 else None
    max_events = args.max_events

    # Exponential backoff state for reconnects
    current_reconnect_delay = args.reconnect_delay
    _MAX_RECONNECT_DELAY = 60

    # ── Graceful shutdown ────────────────────────────────────────────────────
    _stop = [False]

    def _handle_signal(sig: int, _frame: object) -> None:
        log.info("Signal %d received; stopping …", sig)
        _stop[0] = True

    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    event_count = 0
    exit_code = 0

    try:
        while not _stop[0]:
            if deadline and time.monotonic() >= deadline:
                log.info("Timeout reached, exiting.")
                break

            proc = None
            connected_ok = False
            try:
                proc = subprocess.Popen(
                    ssh_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
                log.info("Connected. Listening for events (PID %d) …", proc.pid)
                connected_ok = True
                current_reconnect_delay = args.reconnect_delay  # reset on success

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

                    # 1. Emit to stdout
                    emit_event(event, args.pretty, args.summary)
                    event_count += 1

                    if not args.dry_run:
                        # 2. Persist to file first (safety net before push)
                        if output_path:
                            write_event_to_file(output_path, event, args.atomic_write)
                        # 3. Send to HTTP hook
                        if hook_url:
                            send_event_to_hook(
                                event, hook_url, hook_token or None,
                                args.hook_retries, args.hook_timeout,
                                outbox_path, args.atomic_write,
                            )
                    else:
                        log.debug("dry-run: skipped file/hook for event type=%s",
                                  event.get("type"))

                    if max_events > 0 and event_count >= max_events:
                        log.info("Reached max-events=%d, exiting.", max_events)
                        _stop[0] = True
                        break

                proc.wait()
                stderr_output = proc.stderr.read().strip() if proc.stderr else ""

                if _stop[0]:
                    break

                if proc.returncode != 0:
                    log.warning("SSH process exited with code %d.", proc.returncode)
                    if stderr_output:
                        log.debug("SSH stderr: %s", stderr_output)
                    _log_ssh_error(stderr_output, cfg)
                    if not args.reconnect:
                        exit_code = proc.returncode or 1
                        break
                else:
                    log.info("SSH connection closed normally.")
                    if not args.reconnect:
                        break

            except OSError as exc:
                log.warning("SSH launch error: %s", exc)
                if "No such file" in str(exc) or "not found" in str(exc).lower():
                    log.error("'ssh' is not installed or not in PATH. Install OpenSSH.")
                else:
                    log.debug("Verify: ssh_host=%r, ssh_port=%s, ssh_username=%r",
                              cfg.get("ssh_host"), cfg.get("ssh_port"), cfg.get("ssh_username"))
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
                log.info("Reconnecting in %ds …", current_reconnect_delay)
                for _ in range(current_reconnect_delay * 10):
                    if _stop[0]:
                        break
                    time.sleep(0.1)
                if not connected_ok:
                    # Back off only when the connect itself failed (not a mid-stream drop)
                    current_reconnect_delay = min(
                        current_reconnect_delay * 2, _MAX_RECONNECT_DELAY
                    )

    finally:
        if pid_file_path:
            try:
                Path(pid_file_path).unlink(missing_ok=True)
            except OSError:
                pass
        log.info("Done. Total events emitted: %d", event_count)

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
    # ── Config ────────────────────────────────────────────────────────────────
    parser.add_argument("--config", metavar="FILE", default=None,
                        help="Config file (searches 7 default locations if omitted)")
    # ── Filtering ─────────────────────────────────────────────────────────────
    parser.add_argument("--filter",  metavar="TYPES", default="",
                        help="Comma-separated event types to include (default: all)")
    parser.add_argument("--project", metavar="NAMES", default="",
                        help="Comma-separated project names to filter")
    parser.add_argument("--branch",  metavar="NAMES", default="",
                        help="Comma-separated branch names to filter")
    # ── File output ───────────────────────────────────────────────────────────
    parser.add_argument("--output", metavar="PATH", default="",
                        help="Append events to PATH as compact JSONL")
    parser.add_argument("--no-output", action="store_true",
                        help="Disable file output even if --output is set")
    parser.add_argument("--atomic-write", dest="atomic_write",
                        action="store_true", default=True,
                        help="Atomic O_APPEND+fsync writes (default: on)")
    parser.add_argument("--no-atomic-write", dest="atomic_write",
                        action="store_false",
                        help="Disable atomic file writes (compatibility mode)")
    # ── HTTP hook ─────────────────────────────────────────────────────────────
    parser.add_argument("--hook-url", metavar="URL", default="",
                        help="POST each event as JSON to this URL")
    parser.add_argument("--hook-token", metavar="TOKEN", default="",
                        help="X-Auth-Token header value (never logged)")
    parser.add_argument("--hook-retries", metavar="N", type=int, default=3,
                        help="Max hook retries on 5xx/network error (default: 3)")
    parser.add_argument("--hook-timeout", metavar="SECS", type=float, default=3.0,
                        help="HTTP request timeout in seconds (default: 3)")
    parser.add_argument("--outbox", metavar="PATH", default="",
                        help="Append undelivered events here (default: events.outbox.jsonl)")
    # ── Daemon / process ──────────────────────────────────────────────────────
    parser.add_argument("--pid-file", metavar="PATH", default="",
                        help="Write PID to PATH on startup; remove on clean exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and print events; skip all file writes and hooks")
    # ── Stream control ────────────────────────────────────────────────────────
    parser.add_argument("--max-events",      metavar="N",    type=int, default=0,
                        help="Stop after N events (0 = unlimited)")
    parser.add_argument("--timeout",         metavar="SECS", type=int, default=0,
                        help="Stop after SECS seconds (0 = unlimited)")
    parser.add_argument("--reconnect",       action="store_true",
                        help="Reconnect on connection loss (exponential back-off)")
    parser.add_argument("--reconnect-delay", metavar="N", type=int, default=5,
                        help="Initial reconnect delay in seconds (default: 5)")
    # ── Display ───────────────────────────────────────────────────────────────
    parser.add_argument("--pretty",  action="store_true",
                        help="Pretty-print JSON output to stdout")
    parser.add_argument("--summary", action="store_true",
                        help="Emit one-line human-readable summaries instead of JSON")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable DEBUG-level logging")
    parser.add_argument("--quiet",   action="store_true",
                        help="Suppress all log output")
    parser.add_argument("--help", "-h", action="help",
                        help="Show this help and exit")

    args = parser.parse_args()
    sys.exit(stream_events(args))


if __name__ == "__main__":
    main()
