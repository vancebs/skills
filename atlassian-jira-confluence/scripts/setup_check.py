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


def check_env():
    """Check required environment variables."""
    issues = []
    vars_checked = {
        "CONFLUENCE_URL": os.environ.get("CONFLUENCE_URL"),
        "CONFLUENCE_PAT_TOKEN": os.environ.get("CONFLUENCE_PAT_TOKEN"),
        "JIRA_URL": os.environ.get("JIRA_URL"),
        "JIRA_PAT_TOKEN": os.environ.get("JIRA_PAT_TOKEN"),
    }
    for name, val in vars_checked.items():
        if val:
            # Mask token values
            display = val if "URL" in name else val[:4] + "****"
            print(f"[OK] {name} = {display}")
        else:
            print(f"[MISSING] {name} is not set")
            issues.append(name)

    if issues:
        print("\nTo set missing variables:")
        print("  Windows CMD:        set VAR=value")
        print("  Windows PowerShell: $env:VAR = 'value'")
        print("  Linux/macOS:        export VAR=value")
    return len(issues) == 0


def test_jira_connection():
    url = os.environ.get("JIRA_URL")
    token = os.environ.get("JIRA_PAT_TOKEN")
    if not url or not token:
        print("[SKIP] Jira connection test — credentials missing")
        return
    try:
        from atlassian import Jira
        cloud = "atlassian.net" in url
        if cloud:
            username = os.environ.get("JIRA_USERNAME", "")
            jira = Jira(url=url, username=username, password=token, cloud=True)
        else:
            jira = Jira(url=url, token=token)
        info = jira.get_server_info()
        version = info.get("version", "unknown")
        print(f"[OK] Jira connection OK — version {version}")
    except Exception as e:
        print(f"[ERROR] Jira connection failed: {e}")


def test_confluence_connection():
    url = os.environ.get("CONFLUENCE_URL")
    token = os.environ.get("CONFLUENCE_PAT_TOKEN")
    if not url or not token:
        print("[SKIP] Confluence connection test — credentials missing")
        return
    try:
        from atlassian import Confluence
        cloud = "atlassian.net" in url
        if cloud:
            username = os.environ.get("CONFLUENCE_USERNAME", "")
            confluence = Confluence(url=url, username=username, password=token, cloud=True)
        else:
            confluence = Confluence(url=url, token=token)
        spaces = confluence.get_all_spaces(start=0, limit=1)
        print(f"[OK] Confluence connection OK — spaces reachable")
    except Exception as e:
        print(f"[ERROR] Confluence connection failed: {e}")


if __name__ == "__main__":
    print("=== Atlassian Skill Setup Check ===\n")
    sdk_ok = check_sdk()
    print()
    env_ok = check_env()
    print()
    if sdk_ok:
        test_jira_connection()
        test_confluence_connection()

    print("\n=== Done ===")
    sys.exit(0 if sdk_ok else 1)
