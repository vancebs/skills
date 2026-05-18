#!/usr/bin/env python3
"""
t2_config.py — Centralized configuration management for agent skills.

Storage: ${CFG_DIR}/<namespace>.json  (flat JSON object, one file per namespace)

Usage:
    python3 t2_config.py get    <namespace>/<key>
    python3 t2_config.py set    <namespace>/<key> <value>
    python3 t2_config.py list   [<namespace>]
    python3 t2_config.py delete <namespace>/<key>

Exit codes:
    0 — success
    1 — error (key not found, bad format, I/O failure, CFG_DIR not set)
"""

import json
import os
import re
import sys
from pathlib import Path

# ── Validation ────────────────────────────────────────────────────────────────

_NS_RE  = re.compile(r'^[a-z][a-z0-9-]*$')
_KEY_RE = re.compile(r'^[a-z][a-z0-9_-]*$')
_CFG_PATH_RE = re.compile(r'^cfg://([a-z][a-z0-9-]*)/([a-z][a-z0-9_-]*)$')


def _die(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def _cfg_dir() -> Path:
    val = os.environ.get("CFG_DIR", "").strip()
    if not val:
        _die(
            "❌ CFG_DIR 未设置\n"
            "   → 解决方法:\n"
            '     Linux/macOS:  export CFG_DIR="$(pwd)/config"\n'
            "     Windows CMD:  set CFG_DIR=%CD%\\config\n"
            '     PowerShell:   $env:CFG_DIR = "$(Get-Location)\\config"'
        )
    return Path(val)


def _parse_key(raw: str):
    """Split 'namespace/key' into (namespace, key). Die on bad format."""
    # Accept cfg:// URI form
    m = _CFG_PATH_RE.match(raw)
    if m:
        return m.group(1), m.group(2)

    if "/" not in raw:
        _die(
            f"❌ 无效的 key 格式: {raw!r}\n"
            "   格式: <namespace>/<key>  或  cfg://<namespace>/<key>\n"
            "   正则: namespace=[a-z][a-z0-9-]*   key=[a-z][a-z0-9_-]*\n"
            "   例如: gerrit-api/url"
        )

    parts = raw.split("/", 1)
    ns, key = parts[0], parts[1]

    if not _NS_RE.match(ns):
        _die(
            f"❌ 无效的 namespace: {ns!r}\n"
            "   namespace 只能包含小写字母、数字、连字符，且必须以字母开头"
        )
    if "/" in key:
        _die(
            f"❌ 不支持嵌套 key: {raw!r}\n"
            "   key 中不能包含 '/'，嵌套结构不受支持"
        )
    if not _KEY_RE.match(key):
        _die(
            f"❌ 无效的 key: {key!r}\n"
            "   key 只能包含小写字母、数字、下划线、连字符，且必须以字母开头"
        )
    return ns, key


def _config_file(cfg_dir: Path, ns: str) -> Path:
    return cfg_dir / f"{ns}.json"


def _load(cfg_dir: Path, ns: str) -> dict:
    path = _config_file(cfg_dir, ns)
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            _die(f"❌ 配置文件格式错误（根对象必须是 JSON object）: {path}")
        return data
    except json.JSONDecodeError as e:
        _die(f"❌ JSON 解析错误 ({path}): {e}")
    return {}  # unreachable, but satisfies type checker


def _save(cfg_dir: Path, ns: str, data: dict) -> None:
    cfg_dir.mkdir(parents=True, exist_ok=True)
    path = _config_file(cfg_dir, ns)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError as e:
        _die(f"❌ 写入失败 ({path}): {e}")


# ── Value coercion ────────────────────────────────────────────────────────────

def _coerce(raw: str):
    """Convert a CLI string to the most natural JSON-compatible Python type."""
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    if raw.lower() == "null":
        return None
    # Try JSON array / object
    if raw.startswith(("[", "{")):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    # Try int
    try:
        return int(raw)
    except ValueError:
        pass
    # Try float
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


# ── Masking ───────────────────────────────────────────────────────────────────

_SENSITIVE_RE = re.compile(r'password|token|secret|api_key|api_token', re.IGNORECASE)


def _mask(key: str, value) -> str:
    if _SENSITIVE_RE.search(key) and isinstance(value, str) and value:
        return "***"
    return json.dumps(value, ensure_ascii=False)


# ── Subcommands ───────────────────────────────────────────────────────────────

def cmd_get(args):
    if len(args) != 1:
        _die("用法: t2_config.py get <namespace>/<key>")
    cfg_dir = _cfg_dir()
    ns, key = _parse_key(args[0])
    data = _load(cfg_dir, ns)
    if key not in data:
        _die(f"❌ 未找到: cfg://{ns}/{key}  (namespace 文件: {_config_file(cfg_dir, ns)})")
    print(json.dumps(data[key], ensure_ascii=False))


def cmd_set(args):
    if len(args) < 2:
        _die("用法: t2_config.py set <namespace>/<key> <value>")
    cfg_dir = _cfg_dir()
    ns, key = _parse_key(args[0])
    value = _coerce(" ".join(args[1:]))
    data = _load(cfg_dir, ns)
    data[key] = value
    _save(cfg_dir, ns, data)
    print(f"✅ 已设置 cfg://{ns}/{key} = {_mask(key, value)}")


def cmd_list(args):
    cfg_dir = _cfg_dir()
    if args:
        # List keys in a namespace
        ns = args[0]
        if not _NS_RE.match(ns):
            _die(f"❌ 无效的 namespace: {ns!r}")
        data = _load(cfg_dir, ns)
        if not data:
            print(f"(namespace '{ns}' 为空或不存在)")
            return
        for key, val in sorted(data.items()):
            print(f"  {key} = {_mask(key, val)}")
    else:
        # List all namespaces
        if not cfg_dir.exists():
            print("(CFG_DIR 不存在，无命名空间)")
            return
        ns_list = sorted(p.stem for p in cfg_dir.glob("*.json"))
        if not ns_list:
            print("(无命名空间)")
            return
        for ns in ns_list:
            print(ns)


def cmd_delete(args):
    if len(args) != 1:
        _die("用法: t2_config.py delete <namespace>/<key>")
    cfg_dir = _cfg_dir()
    ns, key = _parse_key(args[0])
    data = _load(cfg_dir, ns)
    if key in data:
        del data[key]
        _save(cfg_dir, ns, data)
        print(f"✅ 已删除 cfg://{ns}/{key}")
    else:
        print(f"(cfg://{ns}/{key} 不存在，无需删除)")


# ── Entry point ───────────────────────────────────────────────────────────────

_COMMANDS = {
    "get":    cmd_get,
    "set":    cmd_set,
    "list":   cmd_list,
    "delete": cmd_delete,
}

if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    subcmd = argv[0]
    if subcmd not in _COMMANDS:
        _die(
            f"❌ 未知命令: {subcmd!r}\n"
            f"   可用命令: {', '.join(_COMMANDS)}"
        )
    _COMMANDS[subcmd](argv[1:])
