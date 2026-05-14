#!/usr/bin/env python3
"""
check_env.py — Environment and dependency checker for code-review skill.

Run once when loading the skill to verify everything is properly configured.
All issues are printed with specific guidance to help you fix them.

Usage:
    python3 "$SKILL_DIR/scripts/check_env.py"

Exit codes:
    0 — All checks passed
    1 — One or more checks failed
"""

import json
import os
import platform
import shutil
import ssl
import sys
from base64 import b64encode
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_SKILL_NAME      = "code-review"
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
    return Path(sd).resolve() if sd else Path(__file__).resolve().parent.parent


def _find_config():
    ws = _workspace()
    sd = _skill_dir()
    home = Path.home()
    for p in [
        ws   / "config" / _SKILL_NAME / _CONFIG_FILENAME,
        ws   / "config" / _CONFIG_FILENAME,
        ws   /            _CONFIG_FILENAME,
        sd   /            _CONFIG_FILENAME,
        home / ".config" / _SKILL_NAME / _CONFIG_FILENAME,
        home / ".config" / _CONFIG_FILENAME,
        home /             _CONFIG_FILENAME,
    ]:
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
    suffix = "" if ok else f"  →  需要 Python ≥ 3.9（当前 {v.major}.{v.minor} 不支持 dict|None 类型注解）"
    print(f"{tag} Python {v.major}.{v.minor}.{v.micro}{suffix}")
    return ok


def check_config():
    cfg_path = _find_config()
    if not cfg_path:
        ws  = _workspace()
        sd  = _skill_dir()
        dst = ws / "config" / _SKILL_NAME / _CONFIG_FILENAME
        src = sd / "scripts" / "config.json.example"
        print(f"{_FAIL} 配置文件未找到  →  请创建配置文件：")
        print(f"      # Linux / macOS:")
        print(f"      mkdir -p \"{ws / 'config' / _SKILL_NAME}\"")
        print(f"      cp \"{src}\" \\")
        print(f"         \"{dst}\"")
        print(f"      # Windows PowerShell:")
        print(f"      New-Item -ItemType Directory -Force \"{ws / 'config' / _SKILL_NAME}\"")
        print(f"      Copy-Item \"{src}\" \"{dst}\"")
        print(f"      # 然后用编辑器填写真实的 Gerrit 凭据")
        return None, False

    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        print(f"{_OK} 配置文件: {cfg_path}")
        return cfg, True
    except json.JSONDecodeError as e:
        print(f"{_FAIL} 配置文件 JSON 格式错误: {e}  →  文件: {cfg_path}")
        return None, False


def check_required_fields(cfg):
    ok = True
    fields = {
        "url":      "Gerrit 地址，例如 https://gerrit.example.com",
        "username": "你的 Gerrit 用户名",
        "password": "HTTP Credentials token（Gerrit → Settings → HTTP Credentials → Generate Password）",
    }
    for key, hint in fields.items():
        val = cfg.get(key, "")
        val_str = val.strip() if isinstance(val, str) else str(val)
        if not val_str or val_str.startswith("<"):
            print(f"{_FAIL} 配置缺少必填项: \"{key}\"  →  {hint}")
            ok = False
        else:
            display = "****" if key == "password" else val_str
            print(f"{_OK} {key}: {display}")
    return ok


def _ssl_noverify_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def check_gerrit_rest(cfg):
    url      = cfg.get("url", "").rstrip("/")
    username = cfg.get("username", "")
    password = cfg.get("password", "")
    if not all([url, username, password]):
        print(f"{_WARN}跳过 REST API 测试（配置不完整）")
        return False

    creds = b64encode(f"{username}:{password}".encode()).decode()
    req   = Request(f"{url}/a/accounts/self",
                    headers={"Authorization": f"Basic {creds}"})

    def _try(ctx=None):
        with urlopen(req, timeout=10, context=ctx) as resp:
            body = resp.read().decode("utf-8")
            body = body[5:] if body.startswith(")]}'") else body
            return json.loads(body)

    ssl_disabled = False
    try:
        account = _try()
    except URLError as e:
        reason = getattr(e, "reason", None)
        if isinstance(reason, ssl.SSLError) or "ssl" in str(e).lower():
            print(f"{_WARN}SSL 验证失败，尝试禁用 SSL 验证重试...")
            try:
                account = _try(ctx=_ssl_noverify_context())
                ssl_disabled = True
            except Exception as e2:
                print(f"{_FAIL} Gerrit REST API 连接失败（SSL 禁用后仍失败）: {e2}")
                return False
        else:
            print(f"{_FAIL} 无法连接到 Gerrit: {e.reason}  →  检查网络和 url 配置")
            return False
    except HTTPError as e:
        if e.code == 401:
            print(f"{_FAIL} Gerrit REST API 认证失败 (HTTP 401)  →  请重新生成 HTTP Credentials")
        elif e.code == 404:
            print(f"{_FAIL} Gerrit URL 无法访问 (HTTP 404)  →  检查 url 配置: {url}")
        else:
            print(f"{_FAIL} Gerrit REST API 错误 (HTTP {e.code})")
        return False
    except Exception as e:
        print(f"{_FAIL} REST API 测试异常: {e}")
        return False

    name = account.get("name") or account.get("username") or "unknown"
    ssl_note = "  ⚠️  SSL 验证已禁用（服务器证书不可信）" if ssl_disabled else ""
    print(f"{_OK} Gerrit REST API 连接正常  (账户: {name}){ssl_note}")
    return True


def check_workspace_writable():
    ws   = _workspace()
    test = ws / ".cr_write_test"
    try:
        test.write_text("ok")
        test.unlink()
        print(f"{_OK} Workspace 可写: {ws}")
        return True
    except Exception as e:
        print(f"{_FAIL} Workspace 不可写: {ws}  ({e})")
        return False


def check_gerrit_api_skill():
    """Check if gerrit-api skill is installed (optional companion)."""
    ws   = _workspace()
    home = Path.home()
    for p in [
        ws   / ".agents" / "skills" / "gerrit-api",
        home / ".agents" / "skills" / "gerrit-api",
    ]:
        if p.is_dir():
            print(f"{_OK} gerrit-api skill 已安装: {p}（可用于扩展操作）")
            return True
    print(f"{_WARN}gerrit-api skill 未安装（可选，code-review 自身即可完成基本操作）")
    print(f"      安装: npx skills add https://github.com/vancebs/skills --skill gerrit-api")
    return True  # optional, not blocking


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 62)
    print("  code-review 环境检查")
    print("=" * 62)
    print(f"\n  系统:            {platform.system()} {platform.release()}")
    print(f"  SKILL_WORKSPACE: {_workspace()}")
    print(f"  SKILL_DIR:       {_skill_dir()}")
    print()

    results = {}

    print("─── Python 环境 ──────────────────────────────────────────")
    results["python"] = check_python()

    print("\n─── 配置文件 ─────────────────────────────────────────────")
    cfg, results["config"] = check_config()

    if cfg:
        print("\n─── 必填配置项 ───────────────────────────────────────────")
        results["fields"] = check_required_fields(cfg)

        print("\n─── Gerrit REST API 连接 ──────────────────────────────────")
        results["rest"] = check_gerrit_rest(cfg)

    print("\n─── Workspace 写权限 ─────────────────────────────────────")
    results["workspace"] = check_workspace_writable()

    print("\n─── 可选依赖 ─────────────────────────────────────────────")
    check_gerrit_api_skill()

    print("\n" + "=" * 62)
    fails = [k for k, v in results.items() if not v]
    if not fails:
        print("✅ 所有必要检查通过！可以开始使用 code-review skill。")
        return 0
    else:
        print(f"❌ {len(fails)} 项检查未通过: {', '.join(fails)}")
        print("   按上方提示逐一解决后，重新运行本检查。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
