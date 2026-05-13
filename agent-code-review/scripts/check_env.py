#!/usr/bin/env python3
"""
check_env.py — Environment and dependency checker for agent-code-review skill.

Run once when loading the skill to verify everything is properly configured.
All issues are printed with specific guidance to help you fix them.

Usage:
    python3 "$SKILL_DIR/scripts/check_env.py"

Exit codes:
    0 — All checks passed
    1 — One or more checks failed
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from base64 import b64encode

_SKILL_NAME = "agent-code-review"
_CONFIG_FILENAME = "code_review_config.json"
_OK   = "✅"
_FAIL = "❌"
_WARN = "⚠️ "


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _workspace():
    ws = os.environ.get("SKILL_WORKSPACE", "").strip()
    return Path(ws).resolve() if ws else Path.cwd()


def _skill_dir():
    sd = os.environ.get("SKILL_DIR", "").strip()
    if sd:
        return Path(sd).resolve()
    return Path(__file__).resolve().parent.parent


def _find_config():
    ws = _workspace()
    sd = _skill_dir()
    home = Path.home()
    candidates = [
        ws   / "config" / _SKILL_NAME / _CONFIG_FILENAME,
        ws   / "config" / _CONFIG_FILENAME,
        ws   /            _CONFIG_FILENAME,
        sd   /            _CONFIG_FILENAME,
        home / ".config" / _SKILL_NAME / _CONFIG_FILENAME,
        home / ".config" / _CONFIG_FILENAME,
        home /             _CONFIG_FILENAME,
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_python():
    v = sys.version_info
    ok = v >= (3, 9)
    tag = _OK if ok else _FAIL
    print(f"{tag} Python {v.major}.{v.minor}.{v.micro}", end="")
    if not ok:
        print(f"  →  需要 Python ≥ 3.9（当前版本过低）")
    else:
        print()
    return ok


def check_ssh_binary():
    path = shutil.which("ssh")
    if path:
        print(f"{_OK} SSH 命令: {path}")
        return True
    print(f"{_FAIL} SSH 命令未找到  →  请安装 OpenSSH 客户端")
    if sys.platform == "win32":
        print("      Windows: 设置 → 应用 → 可选功能 → 添加 OpenSSH 客户端")
    elif sys.platform == "darwin":
        print("      macOS: brew install openssh")
    else:
        print("      Linux: sudo apt install openssh-client  或  sudo yum install openssh")
    return False


def check_config():
    cfg_path = _find_config()
    if not cfg_path:
        ws  = _workspace()
        sd  = _skill_dir()
        dst = ws / "config" / _SKILL_NAME / _CONFIG_FILENAME
        src = sd / "scripts" / "config.json.example"
        print(f"{_FAIL} 配置文件未找到  →  请创建配置文件：")
        print(f"      mkdir -p \"{ws / 'config' / _SKILL_NAME}\"")
        print(f"      cp \"{src}\" \\")
        print(f"         \"{dst}\"")
        print(f"      # 然后用编辑器填写 Gerrit 凭据")
        return None, False

    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        print(f"{_OK} 配置文件: {cfg_path}")
        return cfg, True
    except json.JSONDecodeError as e:
        print(f"{_FAIL} 配置文件 JSON 格式错误: {e}")
        print(f"      文件: {cfg_path}")
        return None, False


def check_required_fields(cfg):
    ok = True
    fields = {
        "url":      "Gerrit 地址，例如 https://gerrit.example.com",
        "username": "你的 Gerrit 用户名",
        "password": "HTTP Credentials token（Gerrit → Settings → HTTP Credentials → Generate Password）",
    }
    for key, hint in fields.items():
        val = cfg.get(key, "").strip() if isinstance(cfg.get(key), str) else ""
        if not val:
            print(f"{_FAIL} 配置缺少必填项: \"{key}\"  →  {hint}")
            ok = False
        else:
            display = "****" if key == "password" else val
            print(f"{_OK} {key}: {display}")
    return ok


def check_gerrit_rest(cfg):
    url      = cfg.get("url", "").rstrip("/")
    username = cfg.get("username", "")
    password = cfg.get("password", "")
    if not all([url, username, password]):
        print(f"{_WARN}跳过 REST API 测试（配置不完整）")
        return False

    creds    = b64encode(f"{username}:{password}".encode()).decode()
    req      = Request(f"{url}/a/accounts/self",
                       headers={"Authorization": f"Basic {creds}"})
    try:
        with urlopen(req, timeout=10) as resp:
            body    = resp.read().decode("utf-8")
            body    = body[5:] if body.startswith(")]}'") else body
            account = json.loads(body)
            name    = account.get("name") or account.get("username") or "unknown"
            print(f"{_OK} Gerrit REST API 连接正常  (账户: {name})")
            return True
    except HTTPError as e:
        if e.code == 401:
            print(f"{_FAIL} Gerrit REST API 认证失败 (HTTP 401)")
            print(f"      →  HTTP Password 不正确，请到 Gerrit → Settings → HTTP Credentials → Generate Password 重新生成")
        elif e.code == 404:
            print(f"{_FAIL} Gerrit URL 无法访问 (HTTP 404)  →  检查 url 配置: {url}")
        else:
            print(f"{_FAIL} Gerrit REST API 错误 (HTTP {e.code})")
        return False
    except URLError as e:
        print(f"{_FAIL} 无法连接到 Gerrit: {e.reason}  →  检查网络和 url 配置")
        return False
    except Exception as e:
        print(f"{_FAIL} REST API 测试异常: {e}")
        return False


def check_ssh_connection(cfg):
    from urllib.parse import urlparse
    url      = cfg.get("url", "")
    parsed   = urlparse(url)
    ssh_host = cfg.get("ssh_host", "").strip() or parsed.hostname or ""
    ssh_port = int(cfg.get("ssh_port", 29418))
    ssh_user = cfg.get("ssh_username", "").strip() or cfg.get("username", "").strip()
    ssh_key  = cfg.get("ssh_key", "").strip()

    if not ssh_host:
        print(f"{_WARN}跳过 SSH 测试（无法确定 ssh_host，请在配置中设置）")
        return False

    cmd = [
        "ssh", "-p", str(ssh_port),
        "-o", "ConnectTimeout=10",
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
    ]
    if ssh_key:
        cmd += ["-i", str(Path(ssh_key).expanduser())]
    cmd += [f"{ssh_user}@{ssh_host}", "gerrit", "version"]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            print(f"{_OK} SSH 连接正常  ({r.stdout.strip()})")
            return True
        err = (r.stderr or "").strip()
        print(f"{_FAIL} SSH 连接失败")
        if "Permission denied" in err or "publickey" in err:
            print(f"      →  SSH 密钥认证失败")
            print(f"      →  请到 Gerrit → Settings → SSH Keys → Add Key 上传公钥")
            print(f"      →  公钥文件: ~/.ssh/id_rsa.pub 或 ~/.ssh/id_ed25519.pub")
        elif "Connection refused" in err:
            print(f"      →  连接被拒绝，检查 ssh_host={ssh_host} 和 ssh_port={ssh_port}")
        elif "access denied" in err.lower():
            print(f"      →  账号无 Stream Events 权限，请 Gerrit 管理员在 Global Capabilities 中授权")
        else:
            print(f"      错误详情: {err}")
        return False
    except subprocess.TimeoutExpired:
        print(f"{_FAIL} SSH 连接超时 ({ssh_host}:{ssh_port})")
        return False
    except FileNotFoundError:
        print(f"{_FAIL} ssh 命令不存在")
        return False


def check_workspace_writable():
    ws   = _workspace()
    test = ws / ".acr_write_test"
    try:
        test.write_text("ok")
        test.unlink()
        print(f"{_OK} Workspace 可写: {ws}")
        return True
    except Exception as e:
        print(f"{_FAIL} Workspace 不可写: {ws}  ({e})")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 62)
    print("  agent-code-review 环境检查")
    print("=" * 62)

    import platform
    print(f"\n  系统:            {platform.system()} {platform.release()}")
    print(f"  SKILL_WORKSPACE: {_workspace()}")
    print(f"  SKILL_DIR:       {_skill_dir()}")
    print()

    results = {}

    print("─── Python 环境 ──────────────────────────────────────────")
    results["python"] = check_python()

    print("\n─── SSH 命令 ─────────────────────────────────────────────")
    results["ssh_binary"] = check_ssh_binary()

    print("\n─── 配置文件 ─────────────────────────────────────────────")
    cfg, results["config"] = check_config()

    if cfg:
        print("\n─── 必填配置项 ───────────────────────────────────────────")
        results["fields"] = check_required_fields(cfg)

        print("\n─── Gerrit REST API 连接 ──────────────────────────────────")
        results["rest"] = check_gerrit_rest(cfg)

        print("\n─── Gerrit SSH 连接 ───────────────────────────────────────")
        results["ssh_gerrit"] = check_ssh_connection(cfg)

    print("\n─── Workspace 写权限 ─────────────────────────────────────")
    results["workspace"] = check_workspace_writable()

    print("\n" + "=" * 62)
    fails = [k for k, v in results.items() if not v]
    if not fails:
        print("✅ 所有检查通过！可以开始配置 cron job 使用 agent-code-review。")
        return 0
    else:
        print(f"❌ {len(fails)} 项检查未通过: {', '.join(fails)}")
        print("   按上方提示逐一解决后，重新运行本检查。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
