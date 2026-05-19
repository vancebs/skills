---
name: skill-guide
description: >
  This skill should be used when the user encounters a path error, SKILL_DIR
  issue, config loading failure, or any problem using an installed skill (PART 1);
  or asks to "create a skill", "write a SKILL.md", "improve skill description",
  "add harness engineering", or needs skill authoring standards (PART 2).
  Supplements skill-creator with detailed rules, templates, and Harness Engineering
  constraints. Trigger on: FileNotFoundError, 路径错误, skill authoring, check_env,
  WORKSPACE.
keywords:
  - skill
  - guide
  - path
  - workspace
  - WORKSPACE
  - configuration
  - troubleshooting
  - skill-authoring
  - skill-creation
  - check_env
  - SKILL_DIR
  - harness engineering
triggers:
  - skill-guide
  - skill 创建规范
  - skill authoring
  - 路径错误
  - FileNotFoundError
  - 配置未加载
  - SKILL_DIR
  - check_env
  - WORKSPACE
---

# Skill Guide

> **两大功能 — 按需跳转：**
> - 📖 **调用 skill 时遇到问题** → [PART 1 — 调用指引](#part-1)
> - ✏️ **创建或改进 skill** → [PART 2 — 创建规范](#part-2)

<a name="index"></a>
## 📌 功能索引（读本文档前先看这里）

### PART 1 快速导航

常用入口： [§ 1.2 会话初始化](#section-1-2)、[§ 错误 1](#error-1)、[§ 错误 2](#error-2)、[§ 错误 5](#error-5)、[§ 错误 7](#error-7)、[§ 1.7 快速参考卡](#section-1-7)。

### PART 2 快速导航

常用入口： [§ 2.0 原则总览](#section-2-0)、[§ 规范 3](#rule-3)、[§ 规范 8](#rule-8)、[§ 规范 10](#rule-10)、[§ 规范 11](#rule-11)、[§ 规范 12](#rule-12)。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---

<a name="part-1"></a>
## PART 1 — Skill 调用指引

> 本部分帮助 agent 正确调用已安装的 skill，解决路径、配置、跨平台等常见问题。
> **何时需要：** 首次使用任何 skill 时；遇到路径/配置错误时；cd 后调用 skill 时。

<a name="section-1-1"></a>
### 1.1 核心概念：三个根目录

在调用 skill 时，始终需要区分以下三个不同的目录。**混淆它们是能力较弱的模型最常见的错误来源。**

| 变量          | 含义                 | 典型路径                                                                                       | 用于               |
| ----------- | ------------------ | ------------------------------------------------------------------------------------------ | ---------------- |
| `WORKSPACE` | Agent 的**项目工作目录**  | `/home/user/myproject`                                                                     | 配置文件、输出文件、日志     |
| `SKILL_DIR` | **当前 skill 的安装目录** | `/home/user/myproject/.agents/skills/gerrit-api`或者``/home/user/.agents/skills/gerrit-api`` | 该 skill 自带的脚本和文件 |
| `$HOME`     | 用户主目录              | `/home/user`                                                                               | 全局配置、全局安装的 skill |

> ❌ **错误做法：** 以 `pwd` 或相对路径调用 skill 脚本，或以 `pwd` 拼接配置文件路径。
>
> ✅ **正确做法：** 调用脚本时用 `$SKILL_DIR`，查找配置时用 `$WORKSPACE`。

---

<a name="section-1-2"></a>
### 1.2 会话初始化（Pre-session Checklist）

在使用任何 skill 之前，**必须**完成以下步骤。这是所有后续操作的基础。

### Step 1 — 记录 Workspace

> **为什么：** 如果之后执行了 `cd`，`pwd` 会变化，但 `WORKSPACE` 不变。

```bash
# Linux / macOS / Git Bash
export WORKSPACE="$(pwd)"

# Windows CMD
set WORKSPACE=%CD%

# Windows PowerShell
$env:WORKSPACE = (Get-Location).Path
```

**记住：一旦设置，整个会话中不要再修改它。**

### Step 2 — 确认 Skill 安装目录

对每一个即将使用的 skill，检测并设置其 `SKILL_DIR`。

> **⚠️ v2.0 起变化：** 各 skill 的 SKILL.md 不再包含 SKILL_DIR 检测代码，改用**路径约定**注释。
> 若 agent 平台自动注入 SKILL_DIR，直接使用即可。
> 手动检测方法（特殊需求时使用）见下方。

**自动检测（推荐，跨平台）：**

```python
# 将下方代码保存为临时文件后运行，或作为 python3 -c 的内容
import os, sys
from pathlib import Path

skill_name = "your-skill-name"  # ← 替换为实际 skill 名称
ws = Path(os.environ.get("WORKSPACE", os.getcwd()))

search_paths = [
    ws / ".agents" / "skills" / skill_name,       # workspace-local 安装
    Path.home() / ".agents" / "skills" / skill_name,  # 全局安装
]

for p in search_paths:
    if p.is_dir():
        print(p)
        sys.exit(0)

print(f"ERROR: skill '{skill_name}' not found in:", file=sys.stderr)
for p in search_paths:
    print(f"  {p}", file=sys.stderr)
sys.exit(1)
```

**设置 SKILL_DIR：**

```bash
# Linux / macOS（将 gerrit-api 替换为实际 skill 名称）
export SKILL_DIR=$(python3 -c "
import os, sys
from pathlib import Path
name = 'gerrit-api'
ws = Path(os.environ.get('WORKSPACE', os.getcwd()))
for p in [ws/'.agents'/'skills'/name, Path.home()/'.agents'/'skills'/name]:
    if p.is_dir():
        print(p); sys.exit(0)
sys.exit(1)
") || echo "ERROR: skill not found — run install command"

# Windows PowerShell
$skillName = 'gerrit-api'
$env:SKILL_DIR = @(
    "$env:WORKSPACE\.agents\skills\$skillName",
    "$HOME\.agents\skills\$skillName"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $env:SKILL_DIR) { Write-Error "Skill '$skillName' not found" }
```

> 如果 agent 平台会自动设置 `SKILL_DIR`，跳过此步骤。

> ⚠️ **注意：** 从 skill v2.0 起，individual skills 不再要求在 SKILL.md 中定义 SKILL_DIR 检测代码。改用**路径约定**注释（见规范 2）。SKILL_DIR 检测仅在有特殊平台需求时保留。

### Step 3 — 验证环境变量已设置

```bash
# 验证两个变量都已设置且目录存在
python3 -c "
import os
from pathlib import Path
ws = os.environ.get('WORKSPACE', '')
sd = os.environ.get('SKILL_DIR', '')
print('WORKSPACE:', ws or '[未设置]', '  exists:', Path(ws).is_dir() if ws else False)
print('SKILL_DIR      :', sd or '[未设置]', '  exists:', Path(sd).is_dir() if sd else False)
"
```

---

<a name="section-1-3"></a>
### 1.3 文件路径规范（规则 1–4）

### 规则 1：调用 Skill 自带脚本 → 用 `$SKILL_DIR` 或路径约定

> **v2.0+ 路径约定：** 从 skill v2.0 起，各 skill 的 SKILL.md 中会注明路径约定，例如：`scripts/...` 路径均相对于本 Skill 目录（`.agents/skills/<skill-name>/`）。OpenClaw 等平台会自动将 skill 目录加入 PATH，直接使用 `scripts/...` 即可。

> **示例说明：** 以下示例以 gerrit-api skill 的 `gerrit_api.py` 脚本为例，演示各种路径写法。`scripts/xxx.py` 代表任意 skill 脚本。

```bash
# ✅ 正确（v2.0+ 路径约定，OpenClaw 自动解析）
python3 scripts/gerrit_api.py query "status:open"   # 示意: gerrit-api skill 脚本

# ✅ 正确（需要 SKILL_DIR 时）
python3 "$SKILL_DIR/scripts/gerrit_api.py" query "status:open"

# ❌ 错误 — WORKSPACE 是项目目录，不是 skill 目录
python3 "$WORKSPACE/scripts/gerrit_api.py" query "status:open"
```

### 规则 2：读取/创建配置文件 → 用环境变量或 JSON 配置文件

> **v2.0+ 推荐：** 支持 JSON 配置文件和环境变量两种方式，配置文件优先级更高。配置文件路径：`$WORKSPACE/.config/{skill-name}.json` 或 `~/.config/{skill-name}.json`。详见 [规范 12](#rule-12)。

```bash
# ✅ 正确（v2.0+ 环境变量，仍完整支持）
export GERRIT_URL="https://gerrit.example.com"
export GERRIT_USERNAME="john.doe"
export GERRIT_HTTP_PASSWORD="your-http-token"

# ✅ 正确（v2.0+ 配置文件，优先级更高）
# 创建 $WORKSPACE/.config/gerrit-api.json：
# { "GERRIT_URL": "...", "GERRIT_USERNAME": "...", "GERRIT_HTTP_PASSWORD": "..." }
```

### 规则 3：配置文件搜索顺序（v2.0+ Python 标准模板）

> **v2.0+ 新格式：** skill 使用 `.config/{skill-name}.json` 格式，路径更简洁。参考 [规范 12](#rule-12) 获取完整实现模板。

```python
import json, os
from pathlib import Path

def _load_file_config(skill_name: str, workspace: str | None = None) -> dict:
    """v2.0+ 标准配置加载（优先级：workspace > home > env var）"""
    candidates = []
    if workspace:
        candidates.append(Path(workspace) / ".config" / f"{skill_name}.json")
    candidates.append(Path.cwd() / ".config" / f"{skill_name}.json")
    candidates.append(Path.home() / ".config" / f"{skill_name}.json")
    for path in candidates:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError):
                pass
    return {}

# 使用：cfg = _load_file_config("gerrit-api")
# 读取：cfg.get("GERRIT_URL") or os.environ.get("GERRIT_URL", "")
```

> **推荐配置文件位置（v2.0+）：** `$WORKSPACE/.config/{skill-name}.json`

### 规则 4：输出文件和日志 → 用 `$WORKSPACE`

```bash
# ✅ 正确 — 输出到项目目录（示意: stream.py 代表任意有输出参数的 skill 脚本）
python3 "$SKILL_DIR/scripts/stream.py" --output "$WORKSPACE/events.jsonl"

# ❌ 错误
python3 "$SKILL_DIR/scripts/stream.py" --output events.jsonl
```

---

<a name="section-1-4"></a>
### 1.4 调用前检查清单

在调用任何 skill 的命令之前，依次确认：

- [ ] `WORKSPACE` 已设置为项目根目录的**绝对路径**
- [ ] `SKILL_DIR` 已指向目标 skill 的**安装目录绝对路径**
- [ ] `python3 --version` 输出 ≥ 3.9（部分 skill 要求）
- [ ] skill 要求的配置文件已存在（路径：`$WORKSPACE/.config/{skill-name}.json`，或环境变量已设置）
- [ ] 所有脚本调用使用 `python3 "$SKILL_DIR/scripts/..."` 形式
- [ ] 所有配置/输出路径使用 `"$WORKSPACE/..."` 形式
- [ ] 如果即将执行 `cd`：确保 `WORKSPACE` 和 `SKILL_DIR` 已提前设置

---

<a name="section-1-5"></a>
### 1.5 常见错误与修复（错误 1–8）

<a name="error-1"></a>
### 错误 1：文件找不到（FileNotFoundError / No such file or directory）

**原因：** 在会话中执行了 `cd`，导致相对路径失效。

**排查步骤：**
```bash
# 检查当前目录
pwd

# 检查是否和 WORKSPACE 一致
echo $WORKSPACE

# 如果不一致，重新设置（但要保持原来的值！）
# 不要用 "$(pwd)" — 此时 pwd 已经是错误的目录
```

**修复：** 在会话最开始执行 Step 1（记录 Workspace），之后永远不修改它。

---

<a name="error-2"></a>
### 错误 2：Config file not found / 配置文件未加载

**原因：** 配置文件不在搜索路径上，或 `WORKSPACE` 指向错误目录。

**排查步骤：**
```python
# 运行此诊断代码（替换 skill_name 和 config_filename）
import os
from pathlib import Path

skill_name = "gerrit-api"
config_filename = "gerrit_config.json"
ws = Path(os.environ.get("WORKSPACE", os.getcwd()))
sd = Path(os.environ.get("SKILL_DIR", "."))
home = Path.home()

candidates = [
    ws / "config" / skill_name / config_filename,
    ws / "config" / config_filename,
    ws / config_filename,
    sd / config_filename,
    home / ".config" / skill_name / config_filename,
    home / ".config" / config_filename,
    home / config_filename,
]

for p in candidates:
    status = "✅ EXISTS" if p.is_file() else "❌ not found"
    print(f"{status}  {p}")
```

**修复：** 在 `✅ EXISTS` 最高优先级路径创建配置文件。

---

<a name="error-3"></a>
### 错误 3：Permission denied / 脚本无法执行

**原因：** Python 脚本没有执行权限（Linux/macOS），或 Python 版本不对。

**修复：**
```bash
# 检查 Python 版本
python3 --version

# 始终使用 "python3 script.py" 形式，不要直接执行 "./script.py"
# ✅ 正确（示意: poll_events.py 代表任意 skill 脚本）
python3 "$SKILL_DIR/scripts/poll_events.py"

# ❌ 可能失败
"$SKILL_DIR/scripts/poll_events.py"
```

Windows 上使用 `python` 代替 `python3`：
```batch
python "%SKILL_DIR%\scripts\poll_events.py"
```

---

<a name="error-4"></a>
### 错误 4：shell 命令中 JSON 参数被截断或解析失败

**原因：** 在 shell 的单引号字符串内使用了单引号（常见于 Python 字典的字符串键 `d['key']`）。

**规则：**
```bash
# ✅ 正确 — 使用双引号包裹 JSON（JSON 本身用双引号）
python3 "$SKILL_DIR/scripts/gerrit_api.py" review 123 current \
  '{"message": "LGTM", "labels": {"Code-Review": 1}}'

# ✅ 如果 JSON 复杂，写到文件再传入
cat > /tmp/review.json << 'EOF'
{"message": "LGTM", "labels": {"Code-Review": 1}}
EOF
python3 "$SKILL_DIR/scripts/gerrit_api.py" review 123 current "$(cat /tmp/review.json)"

# ❌ 错误 — 单引号嵌套
python3 script.py review 123 current '{"message": "it's fine"}'
```

**始终将多行 Python 代码写到 `.py` 文件，不要用 `python3 -c '...'` 内联。**

---

<a name="error-5"></a>
### 错误 5：跨平台路径分隔符问题（Windows）

**规则：**

| 场景 | 正确做法 |
|---|---|
| Python 脚本中拼接路径 | 使用 `Path(base) / "subdir" / "file"` |
| 传给脚本的路径参数 | 使用 `os.path.join()` 或 `Path` 对象 |
| Shell 脚本 | Windows 用 `%VAR%\path`，Linux/macOS 用 `$VAR/path` |
| 永远不要 | 在 Python 中硬编码 `"path/to/file"` 或 `"path\\to\\file"` |

```python
# ✅ 正确（跨平台）
from pathlib import Path
config = Path(os.environ["WORKSPACE"]) / "config" / "myconfig.json"

# ❌ 错误（仅 Linux）
config = os.environ["WORKSPACE"] + "/config/myconfig.json"
```

---

<a name="error-6"></a>
### 错误 6：环境变量在子进程中丢失

**原因：** `export VAR=value` 只在当前 shell 有效；某些 agent 框架的每次工具调用是独立的 shell 进程。

**解决方案：**
- 在每次工具调用的开头重新设置需要的环境变量
- 或使用绝对路径而非依赖环境变量

```bash
# 每次调用脚本时带上 --workspace 参数（显式，不依赖环境变量）
python3 "$SKILL_DIR/scripts/poll_events.py" --workspace "$WORKSPACE"
```

---

<a name="error-7"></a>
### 错误 7：同时使用多个 Skill — SKILL_DIR 冲突

**原因：** 同时使用两个 skill 时，`SKILL_DIR` 只能指向一个。

**解决方案：** 为每个 skill 使用独立的命名变量：

```bash
# ✅ Linux / macOS / Git Bash
export GERRIT_API_SKILL_DIR="$WORKSPACE/.agents/skills/gerrit-api"
export CODE_REVIEW_SKILL_DIR="$WORKSPACE/.agents/skills/code-review"

# 调用时明确指定
python3 "$GERRIT_API_SKILL_DIR/scripts/gerrit_api.py" ...
python3 "$CODE_REVIEW_SKILL_DIR/scripts/check_env.py" ...
```

```powershell
# ✅ Windows PowerShell
$env:GERRIT_API_SKILL_DIR = "$env:WORKSPACE\.agents\skills\gerrit-api"
$env:CODE_REVIEW_SKILL_DIR = "$env:WORKSPACE\.agents\skills\code-review"

# 调用时明确指定
python "$env:GERRIT_API_SKILL_DIR\scripts\gerrit_api.py" ...
python "$env:CODE_REVIEW_SKILL_DIR\scripts\check_env.py" ...
```

```batch
:: ✅ Windows CMD
set GERRIT_API_SKILL_DIR=%WORKSPACE%\.agents\skills\gerrit-api
set CODE_REVIEW_SKILL_DIR=%WORKSPACE%\.agents\skills\code-review

python "%GERRIT_API_SKILL_DIR%\scripts\gerrit_api.py" ...
python "%CODE_REVIEW_SKILL_DIR%\scripts\check_env.py" ...
```

---

<a name="error-8"></a>
### 错误 8：Skill 未安装但尝试使用

**排查：**
```python
# 通用 skill 安装检测（替换 skill_name）
import os, sys
from pathlib import Path

skill_name = "gerrit-api"  # ← 替换
ws = Path(os.environ.get("WORKSPACE", os.getcwd()))

for p in [ws / ".agents" / "skills" / skill_name,
          Path.home() / ".agents" / "skills" / skill_name]:
    if p.is_dir():
        print(f"✅ Found at: {p}")
        sys.exit(0)

print(f"❌ Skill '{skill_name}' not installed.")
print(f"Install: npx skills add https://github.com/vancebs/skills --skill {skill_name}")
```

---

<a name="section-1-6"></a>
### 1.6 通用诊断脚本

遇到任何 skill 相关问题时，运行此脚本获取完整诊断信息：

```python
# 保存为 /tmp/skill_diag.py 并运行: python3 /tmp/skill_diag.py
import os, sys, shutil
from pathlib import Path

print("=" * 60)
print("Skill Environment Diagnostics")
print("=" * 60)

# Python 版本
import platform
print(f"\n[Python]  {sys.version}")
print(f"[OS]      {platform.system()} {platform.release()}")

# 关键目录
ws = os.environ.get("WORKSPACE", "")
sd = os.environ.get("SKILL_DIR", "")
print(f"\n[WORKSPACE]  {ws or '[未设置]'}  "
      f"{'✅ exists' if ws and Path(ws).is_dir() else '❌ missing'}")
print(f"[SKILL_DIR]        {sd or '[未设置]'}  "
      f"{'✅ exists' if sd and Path(sd).is_dir() else '❌ missing'}")
print(f"[HOME]             {Path.home()}")
print(f"[pwd]              {os.getcwd()}")

if ws and os.getcwd() != ws:
    print(f"\n⚠️  WARNING: cwd != WORKSPACE  (pwd 已变更)")

# 已安装的 skills
ws_path = Path(ws) if ws else Path.cwd()
skills_dirs = [
    ws_path / ".agents" / "skills",
    Path.home() / ".agents" / "skills",
]

print("\n[Installed Skills]")
found_any = False
for skills_dir in skills_dirs:
    if skills_dir.is_dir():
        for skill in sorted(skills_dir.iterdir()):
            if skill.is_dir():
                print(f"  {'workspace' if 'WORKSPACE' in str(skills_dir) else 'global':9s}  {skill.name:<30s}  {skill}")
                found_any = True
if not found_any:
    print("  (none found)")

# 工具检查
print("\n[Tools]")
for tool in ["python3", "python", "ssh", "git"]:
    path = shutil.which(tool)
    print(f"  {tool:<10s}  {'✅ ' + path if path else '❌ not found'}")

print("\n" + "=" * 60)
```

---

<a name="section-1-7"></a>
### 1.7 快速参考卡

> 📖 完整速查表见 [`references/quick-reference-card.md`](references/quick-reference-card.md)

**核心变量速查：**

| 变量 | 含义 | 示例 |
|---|---|---|
| `WORKSPACE` | 项目工作目录 | `/home/user/myproject` |
| `SKILL_DIR` | Skill 安装目录 | `/home/user/.agents/skills/gerrit-api` |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---

<a name="part-2"></a>
## PART 2 — Skill 创建规范

> 本部分为 skill 作者提供补充规范，帮助较弱模型也能稳定执行 skill。
>
> 创建新 skill、改进现有 skill 或审查 skill 质量时，请同时参考 `skill-creator`。

<a name="section-2-0"></a>
### 2.0 原则总览

| 原则               | 说明                                                                 |
| ---------------- | ------------------------------------------------------------------ |
| **跨平台优先**        | skill 默认兼顾 Windows、Linux、macOS；若无法跨平台，必须提前声明并询问用户平台 |
| **简洁无歧义**        | 语言直白，不用隐喻，一句话只表达一件事 |
| **结构化层层递进**      | 先给高层概述，再给详细细节 |
| **脚本优先**         | 确定性操作优先用 Python（stdlib）脚本实现 |
| **正则约束**         | 涉及文本匹配时给出正则表达式 |
| **流程可视化**        | 业务流程用 Mermaid 图表达，并显式写出异常处理 |
| **Checklist 驱动** | 每个步骤配 checklist，方便逐项确认 |

---

<a name="rule-1"></a>
### 规范 1：文本表达
保持语言简洁、明确、可执行：每句话只表达一个动作或条件，命令、预期输出和失败处理必须成组出现。这样能减少弱模型对步骤含义的误判。

> 📖 详细说明见 [`references/skill-authoring-rules.md`](references/skill-authoring-rules.md) — 规范 1 节


<a name="rule-2"></a>
### 规范 2：SKILL.md 文档结构
SKILL.md 应使用固定的信息架构，先说明能力和前置条件，再给步骤、配置、流程和命令参考。统一结构能让模型快速定位所需信息，也方便后续扩展参考文件。

> 📖 详细说明见 [`references/skill-authoring-rules.md`](references/skill-authoring-rules.md) — 规范 2 节


<a name="rule-3"></a>
### 规范 3：脚本优先策略
凡是确定性操作都应优先封装成脚本，由模型负责调用而不是重建实现逻辑。脚本需要跨平台、参数清晰、输出结构化，并显式处理错误和 dry-run 场景。

> 📖 详细说明见 [`references/skill-authoring-rules.md`](references/skill-authoring-rules.md) — 规范 3 节


<a name="rule-4"></a>
### 规范 4：正则约束
只要文档要求模型识别、提取或校验格式，就应同时给出明确的正则或等价校验方式。这样可以把格式判断从“猜测”变成“按规则执行”。

> 📖 详细说明见 [`references/skill-authoring-rules.md`](references/skill-authoring-rules.md) — 规范 4 节


<a name="rule-5"></a>
### 规范 5：业务流程描述
业务流程必须同时具备 Checklist、Mermaid 图和异常处理表，覆盖正常路径与异常路径。目标是让模型既知道顺序，也知道出错时如何停、如何重试、如何恢复。

> 📖 详细说明见 [`references/skill-authoring-rules.md`](references/skill-authoring-rules.md) — 规范 5 节


<a name="rule-6"></a>
### 规范 6：快速开始步骤格式
快速开始中的每一步都要写明目的、可直接运行的命令、预期输出与失败处理。步骤模板固定后，模型更容易稳定复现同一操作。

> 📖 详细说明见 [`references/skill-authoring-rules.md`](references/skill-authoring-rules.md) — 规范 6 节


<a name="rule-7"></a>
### 规范 7：其他降低歧义的方法
除主流程外，还要通过枚举值、exit code、JSON Schema、依赖版本和配置表等方式主动消歧。凡是可能被模型“脑补”的地方，都应改成明确列表或结构化定义。

> 📖 详细说明见 [`references/skill-authoring-rules.md`](references/skill-authoring-rules.md) — 规范 7 节


<a name="rule-8"></a>
### 规范 8：Skill 自检脚本（check_env.py）要求
复杂 skill 必须提供 `check_env.py`，按固定顺序检查运行环境、依赖、配置和可写性，并输出统一的 ✅/❌ 结果。模型应把它作为执行前的标准自检入口。

> 📖 详细说明见 [`references/skill-authoring-rules.md`](references/skill-authoring-rules.md) — 规范 8 节


<a name="rule-9"></a>
### 规范 9：模板与参考（非脚本操作）

凡是需要模型自行执行的命令、代码片段或配置，必须在 SKILL.md 中提供**完整可用的模板或示例**。

> 📖 模板格式规范和配置示例见 [`references/prompt-templates.md`](references/prompt-templates.md) — 规范 9 节

<a name="rule-10"></a>
### 规范 10：Prompt 模板（限制模型自由操作空间）

对于需要模型在 agent 平台执行的复杂操作，SKILL.md 必须提供**直接可用的 prompt 模板**。

> 📖 OpenClaw cron/进程管理/报告分发的完整 prompt 模板见 [`references/prompt-templates.md`](references/prompt-templates.md) — 规范 10 节

<a name="rule-11"></a>
### 规范 11：Harness Engineering（非正常路径与约束声明）

Harness Engineering 要求作者显式声明边界、异常路径、幂等性和禁止事项，避免模型在未定义场景下自由发挥。任何可能失败、重试、重复执行或权限不足的情况，都需要提前写清楚处理规则。

> 📖 详细说明见 [`references/skill-authoring-rules.md`](references/skill-authoring-rules.md) — 规范 11 节

<a name="rule-12"></a>
### 规范 12：配置文件与环境变量策略

当 skill 涉及用户配置参数（服务地址、账号、token 等）时，须同时支持 JSON 配置文件和环境变量两种方式，配置文件优先。仅当两种方式均未配置时才引导用户。配置文件非必选项——两种方式等价。

> 📖 详细说明（Python 实现模板、SKILL.md 格式规范、check_env.py 集成）见 [`references/skill-authoring-rules.md`](references/skill-authoring-rules.md) — 规范 12 节

## 📚 参考文件

| 文件 | 内容 |
|---|---|
| [`references/skill-authoring-rules.md`](references/skill-authoring-rules.md) | 规范 1–8, 11–12 的完整说明 |
| [`references/prompt-templates.md`](references/prompt-templates.md) | 规范 9–10：模板库与 Prompt 示例 |
| [`references/quick-reference-card.md`](references/quick-reference-card.md) | 快速参考卡（变量、命令速查）|

<a name="references"></a>
## 参考

- 本仓库所有 skill 的 SKILL.md 均遵循以上规范
- 每个 skill 的 SKILL.md 中的 Step 0 描述了该 skill 的具体环境变量设置方式
