"""
setup_check.py - Verify environment and SDK installation for atlassian-jira-confluence skill.
Usage: python setup_check.py
"""
import sys
import subprocess
import os
import json


def load_config():
    """Return (config_dict, source_path) from the first .atlassian.json found, or ({}, None)."""
    candidates = [
        os.path.join(os.getcwd(), ".atlassian.json"),
        os.path.expanduser("~/.atlassian.json"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path) as fh:
                    return json.load(fh), path
            except json.JSONDecodeError as e:
                print(f"[WARN] Config file {path} is not valid JSON: {e}")
    return {}, None


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
    """Check credentials from config file (priority) and environment variables."""
    config, config_path = load_config()

    if config_path:
        print(f"[OK] Config file found: {config_path}")
    else:
        print("[INFO] No config file found (~/.atlassian.json or ./.atlassian.json)")

    issues = []

    services = {
        "confluence": {
            "url_env": "CONFLUENCE_URL",
            "token_env": "CONFLUENCE_PAT_TOKEN",
            "username_env": "CONFLUENCE_USERNAME",
        },
        "jira": {
            "url_env": "JIRA_URL",
            "token_env": "JIRA_PAT_TOKEN",
            "username_env": "JIRA_USERNAME",
        },
    }

    creds = {}
    for svc, keys in services.items():
        cfg = config.get(svc, {})
        url      = cfg.get("url")      or os.environ.get(keys["url_env"], "")
        token    = cfg.get("token")    or os.environ.get(keys["token_env"], "")
        username = cfg.get("username") or os.environ.get(keys["username_env"], "")

        url_src   = "config" if cfg.get("url")   else ("env" if os.environ.get(keys["url_env"])   else "missing")
        token_src = "config" if cfg.get("token") else ("env" if os.environ.get(keys["token_env"]) else "missing")

        if url:
            print(f"[OK] {svc}.url ({url_src}) = {url}")
        else:
            print(f"[MISSING] {svc}.url — set {keys['url_env']} or add to config file")
            issues.append(f"{svc}.url")

        if token:
            print(f"[OK] {svc}.token ({token_src}) = {token[:4]}****")
        else:
            print(f"[MISSING] {svc}.token — set {keys['token_env']} or add to config file")
            issues.append(f"{svc}.token")

        creds[svc] = {"url": url, "token": token, "username": username}

    if issues:
        print("\nTo fix missing credentials, choose one of:")
        print("  Config file : create ~/.atlassian.json  (see SKILL.md for format)")
        print("  Env vars    :")
        print("    Linux/macOS:        export VAR=value")
        print("    Windows CMD:        set VAR=value")
        print("    Windows PowerShell: $env:VAR = 'value'")

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
        test_jira_connection(creds["jira"])
        test_confluence_connection(creds["confluence"])

    print("\n=== Done ===")
    sys.exit(0 if sdk_ok else 1)
