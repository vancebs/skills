#!/usr/bin/env python3
"""
setup_check.py - Verify environment and SDK installation for atlassian-jira-confluence skill.
Usage: python setup_check.py
"""
import sys
import subprocess
import os


def check_sdk():
    """Install atlassian-python-api if not present."""
    try:
        import atlassian  # noqa: F401
        print("[OK] atlassian-python-api is installed")
        return True
    except ImportError:
        print("[INFO] atlassian-python-api not found. Installing...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "atlassian-python-api"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("[OK] atlassian-python-api installed successfully")
            return True
        else:
            print(f"[ERROR] Installation failed:\n{result.stderr}")
            return False


def check_credentials():
    """Check credentials from environment variables."""
    url      = os.environ.get("ATLASSIAN_URL", "").strip().rstrip("/")
    username = os.environ.get("ATLASSIAN_USERNAME", "").strip()
    token    = os.environ.get("ATLASSIAN_API_TOKEN", "").strip()

    issues = []

    if url:
        print(f"[OK] ATLASSIAN_URL = {url}")
    else:
        print("[MISSING] ATLASSIAN_URL — set ATLASSIAN_URL=https://yourcompany.atlassian.net")
        issues.append("ATLASSIAN_URL")

    if token:
        print(f"[OK] ATLASSIAN_API_TOKEN = {token[:4]}****")
    else:
        print("[MISSING] ATLASSIAN_API_TOKEN — set ATLASSIAN_API_TOKEN=your-api-token")
        issues.append("ATLASSIAN_API_TOKEN")

    if username:
        print(f"[OK] ATLASSIAN_USERNAME = {username}")
    else:
        print("[INFO] ATLASSIAN_USERNAME not set (required for Atlassian Cloud)")

    if issues:
        print("\nTo fix missing credentials:")
        print("  Linux/macOS:        export VAR=value")
        print("  Windows CMD:        set VAR=value")
        print("  Windows PowerShell: $env:VAR = 'value'")

    creds = {"url": url, "username": username, "token": token}
    return len(issues) == 0, creds


def test_jira_connection(creds):
    url, token, username = creds["url"], creds["token"], creds["username"]
    if not url or not token:
        print("[SKIP] Jira connection test — credentials missing")
        return
    try:
        from atlassian import Jira
        cloud = "atlassian.net" in url
        if cloud:
            jira = Jira(url=url, username=username, password=token, cloud=True)
        else:
            jira = Jira(url=url, token=token)
        info = jira.get_server_info()
        version = info.get("version", "unknown")
        print(f"[OK] Jira connection OK — version {version}")
    except Exception as e:
        print(f"[ERROR] Jira connection failed: {e}")


def test_confluence_connection(creds):
    url, token, username = creds["url"], creds["token"], creds["username"]
    if not url or not token:
        print("[SKIP] Confluence connection test — credentials missing")
        return
    try:
        from atlassian import Confluence
        cloud = "atlassian.net" in url
        if cloud:
            confluence = Confluence(url=url, username=username, password=token, cloud=True)
        else:
            confluence = Confluence(url=url, token=token)
        confluence.get_all_spaces(start=0, limit=1)
        print("[OK] Confluence connection OK — spaces reachable")
    except Exception as e:
        print(f"[ERROR] Confluence connection failed: {e}")


if __name__ == "__main__":
    print("=== Atlassian Skill Setup Check ===\n")
    sdk_ok = check_sdk()
    print()
    env_ok, creds = check_credentials()
    print()
    if sdk_ok:
        test_jira_connection(creds)
        test_confluence_connection(creds)

    print("\n=== Done ===")
    sys.exit(0 if sdk_ok else 1)
