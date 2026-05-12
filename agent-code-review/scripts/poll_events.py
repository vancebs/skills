#!/usr/bin/env python3
"""poll_events.py — Atomic event queue consumer for agent-code-review skill.

Usage:
    python3 poll_events.py [--config FILE] [--workspace DIR] [--events-file PATH]
                           [--gerrit-config FILE] [--max-events N] [--dry-run]

Reads all pending patchset-created events from the JSONL queue file produced by
gerrit_stream_events.py, atomically clears the file, fetches the corresponding
patch diffs from Gerrit, and outputs a structured JSON array to stdout for the
agent to review.

Exit codes:
    0  — Success (may have zero events to review)
    1  — Fatal error (config missing, file I/O error, etc.)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.parse
import urllib.request
import base64
from pathlib import Path

# ---------------------------------------------------------------------------
# Config helpers (mirrors gerrit_api.py / gerrit_stream_events.py convention)
# ---------------------------------------------------------------------------

_SKILL_NAME = "agent-code-review"
_CONFIG_FILENAME = "agent_code_review_config.json"
_GERRIT_CONFIG_FILENAME = "gerrit_config.json"
_GERRIT_SKILL_NAME = "gerrit-api"


def _workspace(explicit: str | None = None) -> Path:
    """Return the **agent's project workspace** directory.

    Used for finding config files and output files that belong to the project.
    Priority: explicit arg > SKILL_WORKSPACE env var > cwd.

    NOTE: Do NOT use this to locate this skill's own scripts or assets.
    Use _skill_dir() for that.
    """
    if explicit:
        return Path(explicit).resolve()
    ws = os.environ.get("SKILL_WORKSPACE", "").strip()
    return Path(ws).resolve() if ws else Path(os.getcwd())


def _skill_dir() -> Path:
    """Return this skill's installation directory.

    Used for locating this skill's own scripts, example files, etc.
    Priority: SKILL_DIR env var (set by the agent platform) > derivation from
    __file__ (scripts/ is one level below the skill root).
    """
    sd = os.environ.get("SKILL_DIR", "").strip()
    if sd:
        return Path(sd).resolve()
    return Path(__file__).resolve().parent.parent  # scripts/../ == agent-code-review/


def _find_other_skill_dir(skill_name: str, ws: Path) -> Path | None:
    """Find the installation directory of another skill.

    Tries workspace-local installation first, then global user installation.
    """
    candidates = [
        ws / ".agents" / "skills" / skill_name,
        Path.home() / ".agents" / "skills" / skill_name,
    ]
    for p in candidates:
        if p.is_dir():
            return p
    return None


def _find_config_file(filename: str, skill_name: str, ws: Path) -> Path | None:
    """Search for *filename* across the 7-path priority list."""
    home = Path.home()
    skill_dir = _skill_dir()

    candidates = [
        ws / "config" / skill_name / filename,
        ws / "config" / filename,
        ws / filename,
        skill_dir / filename,
        home / ".config" / skill_name / filename,
        home / ".config" / filename,
        home / filename,
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _preferred_config_path(ws: Path) -> str:
    return str(ws / "config" / _SKILL_NAME / _CONFIG_FILENAME)


def load_config(explicit_path: str | None, ws: Path) -> dict:
    """Load agent-code-review config. Returns {} if no file found."""
    if explicit_path:
        p = Path(explicit_path)
        if not p.is_file():
            logging.error("Config file not found: %s", explicit_path)
            sys.exit(1)
        with open(p) as fh:
            return json.load(fh)

    found = _find_config_file(_CONFIG_FILENAME, _SKILL_NAME, ws)
    if found:
        logging.debug("Loaded config from: %s", found)
        with open(found) as fh:
            return json.load(fh)
    return {}


def load_gerrit_config(explicit_path: str | None, ws: Path) -> dict:
    """Load gerrit-api config. Returns {} if no file found."""
    if explicit_path:
        p = Path(explicit_path)
        if p.is_file():
            with open(p) as fh:
                return json.load(fh)
        return {}

    found = _find_config_file(_GERRIT_CONFIG_FILENAME, _GERRIT_SKILL_NAME, ws)
    if found:
        with open(found) as fh:
            return json.load(fh)
    return {}


# ---------------------------------------------------------------------------
# Queue reader (atomic)
# ---------------------------------------------------------------------------

def _atomic_read_and_clear(path: Path) -> list[str]:
    """Read all lines from *path* and atomically clear (truncate) the file.

    Implementation:
    - On POSIX: rename to a temp file, then process.  The rename is atomic;
      the stream-events writer will recreate the original on next write.
    - On Windows: open with exclusive lock-like semantics, read, then truncate.

    Returns a list of raw strings (one per line in the file).
    """
    if not path.exists() or path.stat().st_size == 0:
        return []

    if os.name == "nt":
        # Windows: read then truncate (no atomic rename, but acceptable for 1-consumer model)
        with open(path, "r+b") as fh:
            data = fh.read()
            fh.seek(0)
            fh.truncate()
        lines = data.decode("utf-8", errors="replace").splitlines()
    else:
        # POSIX: rename is atomic; writer will recreate on next O_CREAT
        tmp = path.with_suffix(".reading")
        os.rename(path, tmp)
        with open(tmp, "rb") as fh:
            data = fh.read()
        tmp.unlink(missing_ok=True)
        lines = data.decode("utf-8", errors="replace").splitlines()

    return [ln for ln in lines if ln.strip()]


# ---------------------------------------------------------------------------
# Gerrit REST helpers
# ---------------------------------------------------------------------------

def _gerrit_request(url: str, username: str, password: str) -> dict | list | None:
    """GET a Gerrit REST endpoint, strip XSSI prefix, return parsed JSON."""
    auth = base64.b64encode(f"{username}:{password}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        # Strip Gerrit XSSI prefix  )]}'\n
        if body.startswith(")]}'"):
            body = body[5:]
        return json.loads(body)
    except Exception as exc:
        logging.warning("Gerrit request failed: %s  url=%s", exc, url)
        return None


def _encode_path(p: str) -> str:
    return urllib.parse.quote(p, safe="")


def fetch_patchset_info(event: dict, gcfg: dict) -> dict:
    """Fetch change details + file list + per-file diffs for the patchset in *event*.

    Returns a dict with keys:
        change_id   — change number (int)
        project     — project name
        branch      — branch name
        subject     — commit subject
        commit_msg  — full commit message (from revisions detail)
        revision    — current revision SHA
        files       — list of {path, status, diff_text}
        error       — error message if fetch failed (string)
    """
    base_url = (gcfg.get("url") or os.environ.get("GERRIT_URL", "")).rstrip("/")
    username = gcfg.get("username") or os.environ.get("GERRIT_USERNAME", "")
    password = gcfg.get("password") or os.environ.get("GERRIT_HTTP_PASSWORD", "")

    if not base_url or not username or not password:
        return {"error": "Gerrit credentials not configured. Check gerrit_config.json or env vars."}

    change = event.get("change", {})
    patch_set = event.get("patchSet", {})
    change_num = change.get("number") or change.get("id")
    revision = patch_set.get("revision", "current")

    if not change_num:
        return {"error": "Event missing change.number"}

    # Fetch change detail with file list
    detail_url = (
        f"{base_url}/a/changes/{change_num}/revisions/{revision}/files/"
    )
    files_data = _gerrit_request(detail_url, username, password)
    if files_data is None:
        return {"error": f"Failed to fetch file list for change {change_num}"}

    # Fetch commit info for commit message
    commit_url = f"{base_url}/a/changes/{change_num}/revisions/{revision}/commit"
    commit_data = _gerrit_request(commit_url, username, password) or {}
    commit_msg = commit_data.get("message", "")

    # Fetch diff for each file (skip /COMMIT_MSG and /MERGE_LIST pseudo-files)
    files = []
    for filepath, finfo in files_data.items():
        if filepath.startswith("/"):
            continue  # pseudo-files
        status = finfo.get("status", "M")  # A=added, D=deleted, M=modified, R=renamed
        diff_url = (
            f"{base_url}/a/changes/{change_num}/revisions/{revision}"
            f"/files/{_encode_path(filepath)}/diff?intraline=true"
        )
        diff_data = _gerrit_request(diff_url, username, password)
        diff_text = _format_diff(diff_data) if diff_data else "(diff not available)"

        files.append({
            "path": filepath,
            "status": status,
            "diff_text": diff_text,
        })

    return {
        "change_id": change_num,
        "project": change.get("project", ""),
        "branch": change.get("branch", ""),
        "subject": change.get("subject", ""),
        "commit_msg": commit_msg,
        "revision": revision,
        "files": files,
    }


def _format_diff(diff_data: dict) -> str:
    """Convert Gerrit unified diff JSON into a compact diff text."""
    lines = []
    for section in diff_data.get("content", []):
        if "ab" in section:
            for ln in section["ab"]:
                lines.append(f"  {ln}")
        if "a" in section:
            for ln in section["a"]:
                lines.append(f"- {ln}")
        if "b" in section:
            for ln in section["b"]:
                lines.append(f"+ {ln}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Read pending Gerrit events from queue and fetch patch diffs."
    )
    p.add_argument("--config", metavar="FILE",
                   help="Path to agent_code_review_config.json")
    p.add_argument("--workspace", metavar="DIR",
                   help="Project workspace root (overrides SKILL_WORKSPACE / cwd)")
    p.add_argument("--events-file", metavar="PATH",
                   help="events.jsonl queue file (overrides config)")
    p.add_argument("--gerrit-config", metavar="FILE",
                   help="Path to gerrit_config.json (overrides auto-search)")
    p.add_argument("--max-events", metavar="N", type=int, default=0,
                   help="Process at most N events (0 = all)")
    p.add_argument("--dry-run", action="store_true",
                   help="Read queue but do not clear it; do not fetch diffs")
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
    gcfg = load_gerrit_config(getattr(args, "gerrit_config", None), ws)

    # Resolve events file path
    events_file_str = (
        getattr(args, "events_file", None)
        or cfg.get("events_file")
        or str(ws / "events.jsonl")
    )
    events_path = Path(events_file_str).expanduser().resolve()

    logging.info("Polling queue: %s", events_path)

    if not events_path.exists():
        logging.info("Queue file does not exist — no events to process.")
        print(json.dumps({"events": [], "test_mode": cfg.get("test_mode", True)}))
        return

    if args.dry_run:
        logging.info("[dry-run] Reading without clearing queue.")
        with open(events_path, "r", encoding="utf-8") as fh:
            raw_lines = [ln.strip() for ln in fh if ln.strip()]
    else:
        raw_lines = _atomic_read_and_clear(events_path)

    logging.info("Read %d raw lines from queue.", len(raw_lines))

    # Parse JSON lines
    events: list[dict] = []
    for raw in raw_lines:
        try:
            ev = json.loads(raw)
            if ev.get("type") == "patchset-created":
                events.append(ev)
        except json.JSONDecodeError as exc:
            logging.warning("Skipping malformed JSON line: %s", exc)

    logging.info("Found %d patchset-created events.", len(events))

    if args.max_events and len(events) > args.max_events:
        logging.info("Limiting to %d events (--max-events).", args.max_events)
        events = events[: args.max_events]

    # Fetch diffs
    results = []
    for ev in events:
        if args.dry_run:
            results.append({
                "event_summary": ev.get("summary", ""),
                "change_id": ev.get("change", {}).get("number"),
                "project": ev.get("change", {}).get("project"),
                "dry_run": True,
            })
        else:
            logging.info(
                "Fetching diff for change %s …", ev.get("change", {}).get("number")
            )
            info = fetch_patchset_info(ev, gcfg)
            info["event_summary"] = ev.get("summary", "")
            info["received_at"] = ev.get("_received_at", "")
            results.append(info)

    output = {
        "test_mode": cfg.get("test_mode", True),
        "events": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
