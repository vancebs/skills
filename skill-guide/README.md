# skill-guide

Skill 使用指引。帮助 agent（尤其是能力较弱的模型）正确调用其他 skill，避免路径错误、配置未加载、跨平台兼容性等常见问题。

## 功能

- 解释 `SKILL_WORKSPACE`（项目目录）和 `SKILL_DIR`（skill 安装目录）的区别与正确用法
- 提供 skill 安装路径自动检测代码片段（跨平台）
- 配置文件搜索顺序规范
- 常见错误场景（8 种）及修复方法
- 通用诊断脚本，可快速定位环境问题
- 快速参考卡（一页总结）

## 使用场景

- 首次接入 skill 仓库时阅读本指引
- 遇到"文件找不到"、"配置未加载"等错误时排查
- 在会话中执行了 `cd` 后调用 skill 出现路径问题时
- 需要同时使用多个 skill 时

## 安装

```bash
npx skills add https://github.com/vancebs/skills --skill skill-guide
```

详细内容见 [SKILL.md](SKILL.md)。
