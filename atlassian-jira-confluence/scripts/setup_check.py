"""
setup_check.py - Verify environment and SDK installation for atlassian-jira-confluence skill.
Usage: python setup_check.py
"""
import sys
import subprocess
import os
import json


CONFIG_FILE = "atlassian_config.json"
CONFIG_KEYS = [
    ("JIRA_URL",              "jira",       "url"),
    ("JIRA_PAT_TOKEN",        "jira",       "token"),
    ("JIRA_USERNAME",         "jira",       "username"),
    ("CONFLUENCE_URL",        "confluence", "url"),
    ("CONFLUENCE_PAT_TOKEN",  "confluence", "token"),
    ("CONFLUENCE_USERNAME",   "confluence", "username"),
]


def load_config():
    """Load atlassian_config.json from cwd if present."""
    config_path = os.path.join(os.getcwd(), CONFIG_FILE)
    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f), config_path
    return {}, None


def get_cred(config, section, key, env_var):
    return config.get(section, {}).get(key) or os.environ.get(env_var)


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


def check_env(config, config_path):
    """Check required credentials (config file takes priority over env vars)."""
    if config_path:
        print(f"[OK] Config file found: {config_path}")
    else:
        print(f"[INFO] No {CONFIG_FILE} found in current directory — using environment variables")

    required = ["JIRA_URL", "JIRA_PAT_TOKEN", "CONFLUENCE_URL", "CONFLUENCE_PAT_TOKEN"]
    issues = []

    for env_var, section, key in CONFIG_KEYS:
        val = get_cred(config, section, key, env_var)
        source = "config" if config.get(section, {}).get(key) else ("env" if os.environ.get(env_var) else None)
        if val:
            display = val if "URL" in env_var or "USERNAME" in env_var else val[:4] + "****"
            print(f"[OK] {env_var} = {display}  (from {source})")
        elif env_var in required:
            print(f"[MISSING] {env_var} is not set")
            issues.append(env_var)
        else:
            print(f"[OPTIONAL] {env_var} is not set (only needed for Atlassian Cloud)")

    if issues:
        print(f"\nTo fix missing credentials, either:")
        print(f"  1. Create {CONFIG_FILE} in the current directory (see SKILL.md for format)")
        print(f"  2. Or set environment variables:")
        print(f"       Windows CMD:        set VAR=value")
        print(f"       Windows PowerShell: $env:VAR = 'value'")
        print(f"       Linux/macOS:        export VAR=value")
    return len(issues) == 0


def test_jira_connection(config):
    url   = get_cred(config, "jira", "url",      "JIRA_URL")
    token = get_cred(config, "jira", "token",    "JIRA_PAT_TOKEN")
    if not url or not token:
        print("[SKIP] Jira connection test — credentials missing")
        return
    try:
        from atlassian import Jira
        cloud = "atlassian.net" in url
        if cloud:
            username = get_cred(config, "jira", "username", "JIRA_USERNAME") or ""
            jira = Jira(url=url, username=username, password=token, cloud=True)
        else:
            jira = Jira(url=url, token=token)
        info = jira.get_server_info()
        version = info.get("version", "unknown")
        print(f"[OK] Jira connection OK — version {version}")
    except Exception as e:
        print(f"[ERROR] Jira connection failed: {e}")


def test_confluence_connection(config):
    url   = get_cred(config, "confluence", "url",   "CONFLUENCE_URL")
    token = get_cred(config, "confluence", "token", "CONFLUENCE_PAT_TOKEN")
    if not url or not token:
        print("[SKIP] Confluence connection test — credentials missing")
        return
    try:
        from atlassian import Confluence
        cloud = "atlassian.net" in url
        if cloud:
            username = get_cred(config, "confluence", "username", "CONFLUENCE_USERNAME") or ""
            confluence = Confluence(url=url, username=username, password=token, cloud=True)
        else:
            confluence = Confluence(url=url, token=token)
        confluence.get_all_spaces(start=0, limit=1)
        print(f"[OK] Confluence connection OK — spaces reachable")
    except Exception as e:
        print(f"[ERROR] Confluence connection failed: {e}")


if __name__ == "__main__":
    print("=== Atlassian Skill Setup Check ===\n")
    sdk_ok = check_sdk()
    print()
    config, config_path = load_config()
    env_ok = check_env(config, config_path)
    print()
    if sdk_ok:
        test_jira_connection(config)
        test_confluence_connection(config)

    print("\n=== Done ===")
    sys.exit(0 if sdk_ok else 1)
