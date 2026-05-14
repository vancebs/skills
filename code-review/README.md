# code-review

按需 Code Review skill。当 agent 收到 Gerrit 变更信息时，自动获取 patch 并执行代码审查。

## 触发条件

收到以下任意内容时使用：
- Gerrit 变更页面链接（`http://...` 或 `https://...`）
- Change number（纯数字，如 `12345`）
- Change-Id（`I` + 40位十六进制）
- Commit SHA（7~40 位十六进制）
- Gerrit stream event JSON 文本

## 快速开始

```bash
# 1. 环境检查
python3 "$SKILL_DIR/scripts/check_env.py"

# 2. 创建配置
mkdir -p "$SKILL_WORKSPACE/config/code-review"
cp "$SKILL_DIR/scripts/config.json.example" \
   "$SKILL_WORKSPACE/config/code-review/code_review_config.json"
# 编辑配置文件，填写 Gerrit url / username / password

# 3. 获取 patch
python3 "$SKILL_DIR/scripts/fetch_patch.py" \
  --workspace "$SKILL_WORKSPACE" \
  --url "https://gerrit.example.com/c/project/+/12345"

# 4. 审查后提交结果
python3 "$SKILL_DIR/scripts/post_result.py" \
  --workspace "$SKILL_WORKSPACE" \
  --change-id 12345 --result PASS --report "审查通过"
```

详细说明见 [SKILL.md](SKILL.md)。
