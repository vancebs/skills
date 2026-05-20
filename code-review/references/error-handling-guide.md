# Code Review — Error Handling & Troubleshooting Guide

> **来源：** code-review skill 参考文件。覆盖每个阶段的已知错误场景、诊断步骤和恢复措施。

---

## 阶段一：输入解析错误

### 无法识别输入类型

**触发条件：** 收到的文本不符合任何已知格式（非 URL、非纯数字、非 Change-Id 格式、非 commit SHA）。

**处理：**
```
停止，输出：
  "❌ 无法识别输入类型。请提供以下之一：
   - Gerrit 变更页面 URL（http/https 开头）
   - Change number（纯数字，如 12345）
   - Change-Id（I + 40位十六进制）
   - Commit SHA（7~40位十六进制）"
```

---

### `query` 命令返回 0 条结果

**触发条件：** 使用 Change-Id 或 commit SHA 查询 Gerrit，返回空列表。

**可能原因：**
- Change-Id 属于另一个 Gerrit 实例
- Commit 尚未推送到此 Gerrit
- Change 已被管理员删除

**处理：**
```
停止，输出：
  "❌ 在此 Gerrit 实例中未找到对应变更。
   请确认：
   1. GERRIT_URL 指向正确的 Gerrit 实例
   2. 提供的 change number / change-id 属于此实例"
```

---

### `query` 返回多条结果（> 5 条）

**触发条件：** 同一 Change-Id 在不同项目中出现多次（跨项目 cherry-pick）。

**处理：**
- ≤ 5 条：使用第一条，在报告中输出 `[🔵 INFO] 多个变更匹配，使用第一条：#{number}`
- > 5 条：停止，请用户提供明确的 change number（纯数字）

---

## 阶段二：Gerrit API 错误

### `get-change` 失败

| HTTP 状态码 | 原因 | 处理 |
|---|---|---|
| 401 | 凭据错误（GERRIT_USERNAME / GERRIT_HTTP_PASSWORD） | 运行 `gerrit-api` skill 的 `check_env.py` 重新验证 |
| 403 | 账号无权限查看该 change | 确认账号已被添加为 reviewer 或有项目访问权限 |
| 404 | Change number 不存在或已删除 | 确认 change number 正确 |
| 5xx | Gerrit 服务端错误 | 等待 30s 后重试，最多 2 次；失败则停止并报告 |

**诊断步骤：**
```bash
# 手动测试连接
python3 .agents/skills/gerrit-api/scripts/gerrit_api.py \
  query "status:open+limit:1"
```

---

### `list-files` 返回空

**触发条件：** 变更仅包含提交信息修改（无文件变更），或所有文件被 `skip_file_patterns` 过滤。

**处理：**
```
输出："所有文件均被跳过，无可审查代码文件。"
审查结果：【PASS】（不 FAIL）
```

---

### `get-diff` 对特定文件失败或返回空

| 场景 | 原因 | 处理 |
|---|---|---|
| 文件已在当前 revision 中删除 | 删除操作无 diff 内容 | 跳过，报告 `[🔵 INFO] 文件已删除，跳过审查` |
| 二进制文件（`.png`, `.jar` 等） | 无文本 diff | 跳过，报告 `[🔵 INFO] 二进制文件，跳过审查` |
| revision 不匹配 | patchset 在查询期间更新 | 重新执行 `get-change` 获取最新 `current_revision` |

---

## 阶段三：审查过程错误

### T2MCodingRule skill 未加载

**触发条件：** T2MCodingRule 未安装或路径不正确。

**处理：**
```
停止，输出：
  "❌ 需要 T2MCodingRule skill。
   安装命令: npx skills add https://github.com/vancebs/skills --skill T2MCodingRule"
```

---

### 无法获取完整 Commit Message

**触发条件：** `get-change` 的 `subject` 字段仅为首行，无法检查完整 commit message 正文。

**处理：** 仅基于 `subject` 审查 CM-1 ~ CM-3，在报告中注明：
```
[🔵 INFO] 仅能获取 commit message 首行（subject），CM-4 ~ CM-10 无法完整验证
```

---


## 依赖检查失败

### gerrit-api skill 未安装

**检测：** `check_env.py` 输出 `❌ gerrit-api skill 未安装`。

**处理：**
```bash
npx skills add https://github.com/vancebs/skills --skill gerrit-api
python3 .agents/skills/code-review/scripts/check_env.py   # 重新检查
```

---

### GERRIT_URL / GERRIT_USERNAME / GERRIT_HTTP_PASSWORD 未设置

**检测：** `check_env.py` 输出 `❌ GERRIT_URL 未设置` 等。

**处理：** 参考 gerrit-api skill 的 Setup Checklist（配置文件 Option A 或环境变量 Option B）。

```bash
# 快速验证
python3 .agents/skills/gerrit-api/scripts/gerrit_api.py query "status:open+limit:1"
```

---

## 诊断命令速查

```bash
# 检查所有依赖和环境变量
python3 .agents/skills/code-review/scripts/check_env.py

# 检查 Gerrit 连接
python3 .agents/skills/gerrit-api/scripts/gerrit_api.py query "status:open+limit:1"

# 手动获取变更信息（替换 12345）
python3 .agents/skills/gerrit-api/scripts/gerrit_api.py get-change 12345

# 手动列出文件
python3 .agents/skills/gerrit-api/scripts/gerrit_api.py list-files 12345
```
