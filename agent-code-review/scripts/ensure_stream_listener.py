#!/usr/bin/env python3
"""ensure_stream_listener.py — Health-check and auto-restart the Gerrit stream listener.

Usage:
    python3 ensure_stream_listener.py [--workspace DIR] [--pid-file PATH]
                                       [--events-file PATH] [--config FILE]
                                       [--dry-run] [--verbose]

Checks whether gerrit_stream_events.py is running (via PID file).
If not running, locates the gerrit-api skill and starts the listener.

Exit codes:
    0 — Listener is already running (or was started successfully)
    1 — Listener is not running and could not be started
    2 — gerrit-api skill not found (install required)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _workspace(explicit: str | None = None) -> Path:
    """Return the agent's project workspace directory."""
    if explicit:
        return Path(explicit).resolve()
    ws = os.environ.get("SKILL_WORKSPACE", "").strip()
    return Path(ws).resolve() if ws else Path.cwd()


def _skill_dir() -> Path:
    """Return this skill's (agent-code-review) installation directory."""
    sd = os.environ.get("SKILL_DIR", "").strip()
    if sd:
        return Path(sd).resolve()
    return Path(__file__).resolve().parent.parent


def _find_gerrit_api_dir(ws: Path) -> Path | None:
    """Locate the gerrit-api skill installation directory.

    Search order:
      1. GERRIT_API_SKILL_DIR env var (explicitly set by user/platform)
      2. {workspace}/.agents/skills/gerrit-api  (workspace-local install)
      3. $HOME/.agents/skills/gerrit-api        (global user install)
    """
    explicit = os.environ.get("GERRIT_API_SKILL_DIR", "").strip()
    if explicit and Path(explicit).is_dir():
        return Path(explicit).resolve()

    candidates = [
        ws / ".agents" / "skills" / "gerrit-api",
        Path.home() / ".agents" / "skills" / "gerrit-api",
    ]
    for p in candidates:
        if p.is_dir():
            return p
    return None


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

_SKILL_NAME = "agent-code-review"
_CONFIG_FILENAME = "agent_code_review_config.json"


def _find_config_file(ws: Path) -> Path | None:
    home = Path.home()
    skill_dir = _skill_dir()
    for p in [
        ws / "config" / _SKILL_NAME / _CONFIG_FILENAME,
        ws / "config" / _CONFIG_FILENAME,
        ws / _CONFIG_FILENAME,
        skill_dir / _CONFIG_FILENAME,
        home / ".config" / _SKILL_NAME / _CONFIG_FILENAME,
        home / ".config" / _CONFIG_FILENAME,
        home / _CONFIG_FILENAME,
    ]:
        if p.is_file():
            return p
    return None


def load_config(explicit_path: str | None, ws: Path) -> dict:
    if explicit_path:
        p = Path(explicit_path)
        if p.is_file():
            with open(p) as fh:
                return json.load(fh)
        return {}
    found = _find_config_file(ws)
    if found:
        with open(found) as fh:
            return json.load(fh)
    return {}


# ---------------------------------------------------------------------------
# PID file helpers
# ---------------------------------------------------------------------------

def _read_pid(pid_file: Path) -> int | None:
    """Read PID from file. Returns None if file missing or invalid."""
    try:
        return int(pid_file.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def _is_process_running(pid: int) -> bool:
    """Return True if a process with *pid* is alive."""
    try:
        os.kill(pid, 0)  # signal 0 = check existence only
        return True
    except (OSError, ProcessLookupError):
        return False


def _write_pid(pid_file: Path, pid: int) -> None:
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid))


# ---------------------------------------------------------------------------
# Listener management
# ---------------------------------------------------------------------------

def start_listener(
    gerrit_api_dir: Path,
    events_file: Path,
    pid_file: Path,
    ws: Path,
    dry_run: bool = False,
) -> bool:
    """Start gerrit_stream_events.py as a background process.

    Returns True if started successfully (or dry-run).
    """
    listener_script = gerrit_api_dir / "scripts" / "gerrit_stream_events.py"
    if not listener_script.is_file():
        logging.error("gerrit_stream_events.py not found at: %s", listener_script)
        return False

    cmd = [
        sys.executable,
        str(listener_script),
        "--workspace", str(ws),
        "--output", str(events_file),
        "--filter", "patchset-created",
        "--reconnect",
        "--pid-file", str(pid_file),
        "--quiet",
    ]

    if dry_run:
        logging.info("[dry-run] Would start: %s", " ".join(cmd))
        return True

    logging.info("Starting stream listener: %s", " ".join(cmd))
    try:
        # Start detached so the listener survives when this script exits
        kwargs: dict = {"start_new_session": True} if os.name != "nt" else {"creationflags": 0x00000008}
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
        # Write PID immediately (listener will overwrite once it starts)
        _write_pid(pid_file, proc.pid)
        logging.info("Stream listener started (PID %d).", proc.pid)
        return True
    except Exception as exc:
        logging.error("Failed to start stream listener: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Health-check and auto-restart the Gerrit stream listener."
    )
    p.add_argument("--workspace", metavar="DIR",
                   help="Project workspace root (overrides SKILL_WORKSPACE / cwd)")
    p.add_argument("--pid-file", metavar="PATH",
                   help="PID file for the stream listener "
                        "(default: {workspace}/gerrit_stream_listener.pid)")
    p.add_argument("--events-file", metavar="PATH",
                   help="events.jsonl queue file "
                        "(default: from config, or {workspace}/events.jsonl)")
    p.add_argument("--config", metavar="FILE",
                   help="Path to agent_code_review_config.json")
    p.add_argument("--gerrit-api-dir", metavar="DIR",
                   help="gerrit-api skill directory (overrides auto-detection)")
    p.add_argument("--dry-run", action="store_true",
                   help="Check only; do not start the listener")
    p.add_argument("--verbose", action="store_true",
                   help="Enable DEBUG logging")
    return p


def main() -> None:
    args = build_arg_parser().parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    ws = _workspace(getattr(args, "workspace", None) or None)
    cfg = load_config(getattr(args, "config", None), ws)

    # Resolve paths
    pid_file_str = getattr(args, "pid_file", None) or str(ws / "gerrit_stream_listener.pid")
    pid_file = Path(pid_file_str).expanduser().resolve()

    events_file_str = (
        getattr(args, "events_file", None)
        or cfg.get("events_file")
        or str(ws / "events.jsonl")
    )
    events_file = Path(events_file_str).expanduser().resolve()

    # Check if listener is already running
    pid = _read_pid(pid_file)
    if pid is not None and _is_process_running(pid):
        logging.info("Stream listener is running (PID %d). Nothing to do.", pid)
        sys.exit(0)

    if pid is not None:
        logging.warning("Stream listener PID %d is no longer running. Restarting…", pid)
    else:
        logging.info("Stream listener not found (no PID file). Starting…")

    # Find gerrit-api skill
    explicit_gerrit_dir = getattr(args, "gerrit_api_dir", None)
    if explicit_gerrit_dir:
        gerrit_api_dir = Path(explicit_gerrit_dir).resolve()
    else:
        gerrit_api_dir = _find_gerrit_api_dir(ws)

    if gerrit_api_dir is None:
        logging.error(
            "gerrit-api skill not found. "
            "Install it with:\n"
            "  npx skills add https://github.com/vancebs/skills --skill gerrit-api\n"
            "Or set GERRIT_API_SKILL_DIR env var to the skill's directory."
        )
        sys.exit(2)

    logging.info("Using gerrit-api skill from: %s", gerrit_api_dir)

    success = start_listener(gerrit_api_dir, events_file, pid_file, ws, args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
