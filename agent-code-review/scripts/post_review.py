#!/usr/bin/env python3
"""post_review.py — Post a code review result to Gerrit.

Usage:
    python3 post_review.py --change-id <id> --revision <rev|current>
                           --report-file <path> --result <PASS|FAIL>
                           [--config FILE] [--gerrit-config FILE]
                           [--workspace DIR] [--dry-run]

Reads the review report from a file (or stdin if --report-file is "-"),
posts it as a comment on the Gerrit change, and (if result is FAIL)
sets the Verified label to -1.

In test_mode (from agent_code_review_config.json), this script will
print the report to stdout and exit WITHOUT posting anything to Gerrit.
Use --force to override test_mode from CLI.

Exit codes:
    0  — Success (or test mode — no Gerrit write)
    1  — Fatal error
    2  — Test mode active (no Gerrit write performed)
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Config helpers (same pattern as poll_events.py and gerrit_api.py)
# ---------------------------------------------------------------------------

_SKILL_NAME = "agent-code-review"
_CONFIG_FILENAME = "agent_code_review_config.json"
_GERRIT_CONFIG_FILENAME = "gerrit_config.json"
_GERRIT_SKILL_NAME = "gerrit-api"


def _workspace(explicit: str | None = None) -> Path:
    """Return the agent's project workspace directory (for config/output files)."""
    if explicit:
        return Path(explicit).resolve()
    ws = os.environ.get("SKILL_WORKSPACE", "").strip()
    return Path(ws).resolve() if ws else Path(os.getcwd())


def _skill_dir() -> Path:
    """Return this skill's installation directory (for own scripts/assets)."""
    sd = os.environ.get("SKILL_DIR", "").strip()
    if sd:
        return Path(sd).resolve()
    return Path(__file__).resolve().parent.parent  # scripts/../ == agent-code-review/


def _find_config_file(filename: str, skill_name: str, ws: Path) -> Path | None:
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


def load_config(explicit_path: str | None, ws: Path) -> dict:
    if explicit_path:
        p = Path(explicit_path)
        if not p.is_file():
            logging.error("Config not found: %s", explicit_path)
            sys.exit(1)
        with open(p) as fh:
            return json.load(fh)
    found = _find_config_file(_CONFIG_FILENAME, _SKILL_NAME, ws)
    if found:
        with open(found) as fh:
            return json.load(fh)
    return {}


def load_gerrit_config(explicit_path: str | None, ws: Path) -> dict:
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
# Gerrit REST POST
# ---------------------------------------------------------------------------

def _gerrit_post(url: str, username: str, password: str, payload: dict) -> tuple[int, str]:
    """POST JSON payload to *url*. Returns (status_code, response_body)."""
    auth = base64.b64encode(f"{username}:{password}".encode()).decode()
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return exc.code, body
    except Exception as exc:
        return -1, str(exc)


def post_review(
    change_id: str | int,
    revision: str,
    report_text: str,
    passed: bool,
    gcfg: dict,
) -> bool:
    """Post review comment + optional Verified=-1 label to Gerrit.

    Returns True on success.
    """
    base_url = (gcfg.get("url") or os.environ.get("GERRIT_URL", "")).rstrip("/")
    username = gcfg.get("username") or os.environ.get("GERRIT_USERNAME", "")
    password = gcfg.get("password") or os.environ.get("GERRIT_HTTP_PASSWORD", "")

    if not base_url or not username or not password:
        logging.error(
            "Gerrit credentials not configured. "
            "Check gerrit_config.json or GERRIT_URL / GERRIT_USERNAME / GERRIT_HTTP_PASSWORD."
        )
        return False

    url = f"{base_url}/a/changes/{change_id}/revisions/{revision}/review"
    payload: dict = {"message": report_text}
    if not passed:
        payload["labels"] = {"Verified": -1}

    status, body = _gerrit_post(url, username, password, payload)

    if 200 <= status < 300:
        action = "comment posted" + ("" if passed else " + Verified=-1 set")
        logging.info("Gerrit review %s (HTTP %d).", action, status)
        return True
    else:
        logging.error(
            "Gerrit review POST failed HTTP %d for change %s: %s",
            status, change_id, body[:200],
        )
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Post a code review result (comment + optional Verified label) to Gerrit."
    )
    p.add_argument("--change-id", required=True,
                   help="Gerrit change number or change ID")
    p.add_argument("--revision", default="current",
                   help="Revision SHA or 'current' (default: current)")
    p.add_argument("--report-file", default="-", metavar="PATH",
                   help="Path to report text file, or '-' to read from stdin")
    p.add_argument("--result", required=True, choices=["PASS", "FAIL"],
                   help="Review result: PASS or FAIL")
    p.add_argument("--config", metavar="FILE",
                   help="Path to agent_code_review_config.json")
    p.add_argument("--gerrit-config", metavar="FILE",
                   help="Path to gerrit_config.json")
    p.add_argument("--workspace", metavar="DIR",
                   help="Project workspace root (overrides SKILL_WORKSPACE / cwd)")
    p.add_argument("--force", action="store_true",
                   help="Override test_mode and post to Gerrit even in test mode")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the payload to stdout; do not POST to Gerrit")
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

    # Read report text
    if args.report_file == "-":
        report_text = sys.stdin.read()
    else:
        rp = Path(args.report_file)
        if not rp.is_file():
            logging.error("Report file not found: %s", rp)
            sys.exit(1)
        report_text = rp.read_text(encoding="utf-8")

    passed = args.result == "PASS"
    test_mode = cfg.get("test_mode", True) and not args.force

    if args.dry_run:
        print(f"[dry-run] Would post to change {args.change_id} revision {args.revision}:")
        print(f"  result: {args.result}")
        print("  report:", report_text[:200], "…" if len(report_text) > 200 else "")
        sys.exit(0)

    if test_mode:
        logging.warning(
            "test_mode=true — NOT posting to Gerrit. "
            "Set test_mode=false in config or pass --force to post."
        )
        print("[TEST MODE] Review report (not posted to Gerrit):")
        print(f"Change: {args.change_id}  Revision: {args.revision}  Result: {args.result}")
        print("-" * 60)
        print(report_text)
        sys.exit(2)

    success = post_review(args.change_id, args.revision, report_text, passed, gcfg)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
