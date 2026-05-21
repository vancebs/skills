# Quick Reference Card

> **来源：** 本文档是 skill-guide 的快速参考内容。遇到 SKILL_DIR / WORKSPACE 相关问题时参考。

<a name="section-1-7"></a>
### 1.7 快速参考卡

打印并贴在显眼位置：

```
┌─────────────────────────────────────────────────────────┐
│  Skill 调用规范 Quick Reference                          │
├─────────────────────────────────────────────────────────┤
│  WORKSPACE  = 项目目录（配置/输出文件）            │
│  SKILL_DIR        = skill 安装目录（脚本/资产）          │
├─────────────────────────────────────────────────────────┤
│  会话开始（Linux/macOS）：                               │
│    export WORKSPACE="$(pwd)"                      │
│    export SKILL_DIR=$(detect-skill-dir "skill-name")    │
│  会话开始（Windows PowerShell）：                        │
│    $env:WORKSPACE = (Get-Location).Path           │
│    $env:SKILL_DIR = "<绝对路径>"                        │
│  会话开始（Windows CMD）：                               │
│    set WORKSPACE=%CD%                             │
│    set SKILL_DIR=<绝对路径>                             │
├─────────────────────────────────────────────────────────┤
│  调用脚本（Linux/macOS）：                               │
│    python3 "$SKILL_DIR/scripts/xxx.py"                  │
│  调用脚本（Windows）：                                   │
│    python "%SKILL_DIR%\scripts\xxx.py"                  │
├─────────────────────────────────────────────────────────┤
│  配置文件：  {WORKSPACE}/config/{skill}/{file}    │
│  输出文件：  {WORKSPACE}/{file}                   │
├─────────────────────────────────────────────────────────┤
│  cd 之前：确保环境变量已设置（不受 cd 影响）             │
│  多 skill：为每个 skill 用不同变量名                    │
│  Python：  始终写 .py 文件，不用 python3 -c '...'      │
│  路径：    始终用 Path() 操作，不硬编码分隔符           │
└─────────────────────────────────────────────────────────┘
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---
