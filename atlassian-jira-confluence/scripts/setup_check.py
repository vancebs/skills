#!/usr/bin/env python3
"""
setup_check.py - Verify environment and SDK installation for atlassian-jira-confluence skill.
Usage: python3 scripts/setup_check.py [--workspace WORKSPACE]

Checks:
  1. atlassian-python-api SDK installed
  2. Jira env vars (JIRA_URL, JIRA_PAT_TOKEN)
  3. Confluence env vars (CONFLUENCE_URL, CONFLUENCE_PAT_TOKEN)
  4. Optional: live connection test for each service

Exit codes:
  0 — all checks passed
  1 — one or more checks failed
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


_OK   = "✅"
_FAIL = "❌"
_INFO = "ℹ️ "


def _load_file_config(skill_name: str, workspace: str | None = None) -> dict:
    """Load JSON config from workspace or home .config directory."""
    candidates = []
    if workspace:
        candidates.append(Path(workspace) / ".config" / f"{skill_name}.json")
    candidates.append(Path.cwd() / ".config" / f"{skill_name}.json")
    candidates.append(Path.home() / ".config" / f"{skill_name}.json")
    seen, search = set(), []
    for p in candidates:
        k = str(p)
        if k not in seen:
            seen.add(k)
            search.append(p)
    for path in search:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def check_sdk():
    """Check atlassian-python-api; offer to install if missing."""
    try:
        import atlassian  # noqa: F401
        print(f"{_OK} atlassian-python-api: installed")
        return True
    except ImportError:
        print(f"{_FAIL} atlassian-python-api not found")
        print("      → 解决方法: pip install atlassian-python-api")
        return False


def _check_service(name: str, url_var: str, token_var: str, user_var: str, cfg: dict) -> dict | None:
    """Check env vars for one Atlassian service. Returns creds dict or None."""
    url   = (cfg.get(url_var) or os.environ.get(url_var, "")).strip().rstrip("/")
    token = (cfg.get(token_var) or os.environ.get(token_var, "")).strip()
    user  = (cfg.get(user_var) or os.environ.get(user_var, "")).strip()

    ok = True
    if url:
        print(f"{_OK} {url_var} = {url}")
    else:
        print(f"{_FAIL} {url_var} 未设置  →  export {url_var}=https://your-{name.lower()}.example.com")
        ok = False

    if token:
        print(f"{_OK} {token_var} = {token[:4]}****")
    else:
        print(f"{_FAIL} {token_var} 未设置  →  export {token_var}=your-pat-token")
        ok = False

    if user:
        print(f"{_OK} {user_var} = {user}")
    else:
        print(f"{_INFO} {user_var} 未设置（仅 Atlassian Cloud 必须）")

    return {"url": url, "token": token, "username": user} if ok else None


def check_credentials(cfg: dict):
    print(f"\n─── Jira ────────────────────────────────────────")
    jira_creds = _check_service("Jira", "JIRA_URL", "JIRA_PAT_TOKEN", "JIRA_USERNAME", cfg)

    print(f"\n─── Confluence ──────────────────────────────────")
    conf_creds = _check_service("Confluence", "CONFLUENCE_URL", "CONFLUENCE_PAT_TOKEN", "CONFLUENCE_USERNAME", cfg)

    return jira_creds, conf_creds


def _is_cloud(url: str) -> bool:
    return "atlassian.net" in url


def test_jira_connection(creds: dict):
    url, token, username = creds["url"], creds["token"], creds["username"]
    try:
        from atlassian import Jira
        jira = (Jira(url=url, username=username, password=token, cloud=True)
                if _is_cloud(url) else Jira(url=url, token=token))
        info = jira.get_server_info()
        print(f"{_OK} Jira 连接成功 — version {info.get('version', 'unknown')}")
    except Exception as e:
        print(f"{_FAIL} Jira 连接失败: {e}")


def test_confluence_connection(creds: dict):
    url, token, username = creds["url"], creds["token"], creds["username"]
    try:
        from atlassian import Confluence
        conf = (Confluence(url=url, username=username, password=token, cloud=True)
                if _is_cloud(url) else Confluence(url=url, token=token))
        conf.get_all_spaces(start=0, limit=1)
        print(f"{_OK} Confluence 连接成功")
    except Exception as e:
        print(f"{_FAIL} Confluence 连接失败: {e}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", help="Workspace path for config lookup")
    args = parser.parse_args()

    print("=" * 52)
    print("  atlassian-jira-confluence 环境检查")
    print("=" * 52)

    cfg = _load_file_config("atlassian-jira-confluence", args.workspace)
    if cfg:
        print(f"{_INFO} 配置来源: 配置文件")
    else:
        print(f"{_INFO} 配置来源: 环境变量")

    sdk_ok = check_sdk()
    jira_creds, conf_creds = check_credentials(cfg)

    if sdk_ok:
        print(f"\n─── 连接测试 ────────────────────────────────────")
        if jira_creds:
            test_jira_connection(jira_creds)
        else:
            print(f"{_INFO} Jira 连接测试跳过（凭据缺失）")
        if conf_creds:
            test_confluence_connection(conf_creds)
        else:
            print(f"{_INFO} Confluence 连接测试跳过（凭据缺失）")

    print("\n" + "=" * 52)
    if sdk_ok and jira_creds and conf_creds:
        print(f"{_OK} 所有检查通过！")
        return 0

    print(f"{_FAIL} 存在未通过项，按上方提示逐一解决后重新运行。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
