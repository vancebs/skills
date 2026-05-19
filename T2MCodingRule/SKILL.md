---
name: T2MCodingRule
description: >
  This skill should be used when the user asks about T2Mobile coding standards,
  "git commit message format", "code review rules", "PR flow", "Java naming conventions",
  "C++ coding style", "C coding standards", "security coding requirements",
  "compatibility coding", "ADR", "software release process", or any T2Mobile
  development process question. Covers C/C++/Java style, Gerrit workflow, ADR,
  release process, and test management. Also trigger on: 编码规范, commit message,
  code review, PR流程, 安全规范, 兼容性规范, T2Mobile规范.
keywords:
  - T2MCodingRule
  - coding standards
  - commit message
  - code review
  - PR flow
  - Java
  - C
  - C++
  - security
  - compatibility
  - T2Mobile
triggers:
  - T2MCodingRule
  - 编码规范
  - commit message
  - code review规范
  - PR流程
  - 安全编码
  - 兼容性编码
  - Java规范
  - C规范
  - ADR
---

# T2Mobile 编码规范与开发流程知识库

本skill涵盖T2Mobile公司适用于C/C++/Java开发的完整编码规范、Git提交规范、Code Review规范与流程、问题解决流程（PR流程）、安全编码规范、兼容性编码规范等。

---

## 📖 快速导航（Quick Lookup Guide）

**不确定看哪一节？请参考下表直接跳转：**

| 我需要了解…                 | 查看章节（搜索下方对应标题）                       |
| ---------------------- | ------------------------------------ |
| 如何写 git commit message | **一、Git Commit Message 规范**（本文档）    |
| 提交代码前要检查什么             | **二、代码提交前检查**（本文档）                   |
| Code Review 的流程和要求     | **三、Code Review 规范与流程**（本文档）         |
| Java 代码风格、命名、注释        | [`references/coding-standards.md`](references/coding-standards.md) — 四、Java 编码规范 |
| C 代码风格、命名、注释           | [`references/coding-standards.md`](references/coding-standards.md) — 五、C 编码规范 |
| C++ 代码风格、命名、注释         | [`references/coding-standards.md`](references/coding-standards.md) — 六、C++ 编码规范 |
| 安全编码要求（权限、加密、日志）       | [`references/security-compatibility.md`](references/security-compatibility.md) — 七、安全编码规范 |
| 兼容性编码要求（API、HAL、AIDL）  | [`references/security-compatibility.md`](references/security-compatibility.md) — 八、兼容性编码规范 |
| 什么时候需要做安全/兼容性检测        | [`references/security-compatibility.md`](references/security-compatibility.md) — 九、安全/兼容性检测流程 |
| 架构变更需要写 ADR            | **十、架构决策记录（ADR）**（本文档）              |
| 发现问题如何走 PR 流程          | [`references/process-workflow.md`](references/process-workflow.md) — 十一、问题解决流程 |
| SDK/平台升级规范             | [`references/process-workflow.md`](references/process-workflow.md) — 十二、SDK/平台升级操作规范 |
| 测试管理要求                 | [`references/process-workflow.md`](references/process-workflow.md) — 十三、软件测试管理规定 |
| 软件发布流程                 | [`references/process-workflow.md`](references/process-workflow.md) — 十四、软件发布流程 |
| 需求管理流程                 | [`references/process-workflow.md`](references/process-workflow.md) — 十五、软件需求管理流程 |
| 提交前综合自查清单              | **十六、提交前综合自查清单**（本文档）              |

---

## ⚡ 常见场景速查

### 场景 A — 提交一个 Bug 修复
**步骤：**
1. 检查代码是否符合对应语言的编码规范（Java / C / C++ → [`references/coding-standards.md`](references/coding-standards.md)）
2. 检查是否涉及安全或兼容性变更 → 若是，参考 [`references/security-compatibility.md`](references/security-compatibility.md)
3. 填写 Commit Message（格式见一，必须关联 Jira ID）
4. 勾选 [提交前综合自查清单（十六）]
5. 创建 PR，@相关 Reviewer，遵守 Code Review 流程（三）

### 场景 B — Code Review 一个 PR
**检查清单：**
- [ ] Commit Message 格式正确（见一）
- [ ] 代码符合语言编码规范（见 [`references/coding-standards.md`](references/coding-standards.md)）
- [ ] 无硬编码密码/token/内网地址
- [ ] 涉及安全变更时，按 [`references/security-compatibility.md`](references/security-compatibility.md) 检查权限、日志、加密
- [ ] 涉及兼容性变更时，按 [`references/security-compatibility.md`](references/security-compatibility.md) 检查 API/HAL/AIDL 向后兼容
- [ ] Review 结论符合三中的标准（必须明确 Approved/Needs Changes）

### 场景 C — 发现一个线上问题
**步骤：** 按 [`references/process-workflow.md`](references/process-workflow.md) 中十一（问题解决流程）、十三（测试）、十四（发布）走完整流程：
1. 问题登记（Jira 创建 Bug，填写影响范围）
2. 根因分析（RCA 文档）
3. 修复方案 + 代码 Review
4. 测试验证
5. 发布
6. 回顾（Postmortem）

---

## 一、Git Commit Message 规范

### 1.1 格式模板

```
<Issue Key> <Summary>

* Root Cause
<根因简述>
* Solution
<解决方案简述>
* Test Steps
<自测步骤>
* Test Result
<自测结果>
```

- Issue Key 与 Summary 之间用**空格**分隔
- Issue Key 和 Summary 之间有一行空行分隔

### 1.2 示例

```
[X1-2362] There is no "USB Preference" notification after run command "adb shell xxxxx --xxxxxxx"

* Root Cause
Set persist.vendor.usb.config as "mfg" in --xxxxxxxx

* Solution
Set persist.vendor.usb.config as "none"

* Test Steps
1. Set inproduction flag
2. do factory reset in MMITest
3. Run "adb shell xxxx --xxxxxx" and "adb shell xxxxxx --xxxxxxx"
4. DUT reboot
5. The USB Preference notification should be found when the USB cable is plugged in.

* Test Result
Pass
```

### 1.3 质量要求

- **`* Solution` 字段必须具体描述实际所做的技术改动**，使读者无需查看代码即可理解变更核心内容。
- **禁止**使用无实质意义的表述，例如：
  - "Fix code to meet customer's requirement"
  - "按客户要求修改"
  - "代码优化"
- 正确示例：`Set persist.vendor.usb.config as "none" to restore default USB mode after production flag is set.`
- 错误示例：`Fix code to meet customer's requestment.`

### 1.4 涉及安全/兼容性变更时，追加字段

当变更触发安全或兼容性检查时，在 `* Solution` 段之后追加：

```
* Security Check
<通过 / 不适用，如不适用请注明原因>
* Compatibility Check
<通过 / 不适用，如不适用请注明原因>
```

### 1.5 涉及 ADR 时

若变更涉及对 AOSP 框架目录的改动、新增系统服务、或重大架构调整，Commit Message 中必须包含已审批 ADR 文档的引用

---

## 二、代码提交前检查

开发者在执行 `git push` 提交到 Gerrit 之前，必须确保：

- 代码能**编译通过**，无错误或警告（或警告已被允许）
- 本地已**验证**问题被解决或者开发目的达成
- 不包含**敏感信息**（密码、密钥、token、内网地址）
- **注释完整**、函数/变量命名规范
- 与需求文档/**Jira ID** 对齐
- 禁止上传大文件、二进制、敏感 PD

---

## 三、Code Review 规范与流程

### 3.1 Reviewer 的职责

- 检查代码**逻辑是否正确**
- **风险点、边界条件**是否处理
- **兼容性、安全性、性能**影响
- **命名是否合理**、冗余代码是否清理
- 是否符合编码规范（C/C++/Java 规范）
- **注释是否充分、清晰**
- 检测对于基线代码的修改是否遵守**最小改动原则**
- Commit Message 中的 `* Solution` 是否包含有实质内容的技术描述

### 3.2 Review 要求

- 至少 **1 人** Review，**核心模块**需要 **2 人**（通常可指定 TL 和 SPM）
- Review 通过后方可 merge

### 3.3 静态分析要求

- 必须通过 **SonarQube** 检测（地址：http://172.31.3.62:9000/）
  - 仅检测 patch 改动部分代码
  - 只有 Quality Gate 为 **Passed** 的 patch 才能入库
- 必须通过 XML 完整性检测

### 3.4 AI Code Review（自动）

Gerrit 提交后，AI Code Review 与 SonarQube 扫描**并行触发**，结果以 Gerrit 评论形式发布。

开发工程师必须对每条发现回复处理方式：
- **已修复**：说明修复方式，上传新 patch set
- **误报**：说明判断依据
- **可接受风险**：说明理由，需 STL 确认

未处理 AI Code Review 报告的 patch，STL 不得给出 Code Review +2。

### 3.5 Code Review 结论

- 全部通过：Code Review +2，允许合入
- 发现问题：Code Review -1，在评论中列出不符合的规范条目，开发工程师修改后重新提

---

## ⛔ 约束与禁止事项

### 不支持的场景

| 场景 | 原因 | 处理动作 |
|---|---|---|
| 自动修复 commit message | 不在本 skill 职责范围内 | 输出问题和建议，由提交者手动修改 |
| 生成代码补丁 | 不在本 skill 职责范围内 | 输出问题和建议，不生成代码 |
| 审查已合并代码的正确性（运行时行为）| 静态审查范围 | 标注"本工具仅做静态代码分析，运行时行为需测试验证" |
| 无 Gerrit 连接时审查并发布结果 | 依赖 gerrit-api | 若 gerrit-api 不可用，仅输出报告到会话，不发布到 Gerrit |

### 明确禁止的操作

- ⛔ **禁止跳过任何 `[🟠 ERROR]` 或 `[🔴 CRITICAL]` 级别的问题**：必须在报告中列出
- ⛔ **禁止修改 T2MCodingRule 中的规范内容**（如宽松某条规则以使变更通过）
- ⛔ **禁止对 generated/auto-generated 代码应用命名规范**：以下情况标记 `[🔵 INFO] 疑似自动生成代码，跳过命名规范检查`：
  - 文件路径含 `gen/`, `generated/`, `build/`, `out/`
  - 文件头含 `@generated` 或 `DO NOT EDIT` 注释
- ⛔ **禁止对 AOSP upstream 原始文件（未经修改）应用 T2Mobile 命名规范**：标记 `[🔵 INFO] 疑似 AOSP 原始文件，请人工确认是否适用 T2Mobile 规范`

### 规则冲突处理

当 T2MCodingRule 与 AOSP / upstream 约束冲突时：
1. 标注冲突：`[🟡 WARNING] 与 AOSP/upstream 存在规范冲突`
2. 列出冲突细节
3. **不自动判定 FAIL**；由人工决

---

## 十、架构决策记录（ADR）

以下情况**必须**在开发开始前完成 ADR 并提交评审：

- 对 AOSP 核心框架目录（`frameworks/base`、`frameworks/native`）进行任何改动
- 新增系统服务
- 需要跨模块或跨团队架构设计的重大新功能
- 对现有模块的重大架构调整，影响范围涉及多个组件

**ADR 模板（最低必填章节）：**

```markdown
# ADR: [简要标题]

## 背景
[描述背景及需要解决的问题或需求]

## 已评估的方案

### 方案 A: [名称]
- 描述: ...
- 优点: ...
- 缺点: ...

### 方案 B: [名称]
- 描述: ...
- 优点: ...
- 缺点: ...

## 推荐方案
[说明推荐哪个方案及原因]

## 影响评估
[列出受影响模块、已知风险及迁移注意事项]
```

**ADR 流程：**
1. 开发工程师（在 STL 参与下）编写 ADR
2. STL 内部审查确认
3. SPM 提交客户评审
4. 客户确认后方可开始开发
5. 实施 patch 的 Commit Message 中必须包含已审批 ADR 的引

---

## 十六、提交前综合自查清单

### 通用检查

- [ ] 编译通过，无错误或警告
- [ ] 本地已验证问题解决
- [ ] 无硬编码密码、密钥、token
- [ ] 无敏感信息（内网地址等）
- [ ] 注释完整，命名规范
- [ ] 与 Jira ID 对齐
- [ ] SonarQube Quality Gate 为 Passed

### 安全检查（涉及安全变更时）

- [ ] `AndroidManifest.xml` 无冗余权限
- [ ] `exported=true` 的组件均设置了 `android:permission`
- [ ] Binder/AIDL 接口入口处有权限验证或 UID 校验
- [ ] 无硬编码密码、密钥、token
- [ ] 日志中无敏感信息明文输出
- [ ] 原生程序 SELinux 策略已最小化配置

### 兼容性检查（涉及兼容性变更时）

- [ ] 无新增 `@Deprecated` API 调用
- [ ] HAL 接口修改遵守版本演进规则（不破坏已发布版本）
- [ ] AIDL 接口修改向后兼容（新字段有默认值，未删除已有方法）
- [ ] ContentProvider URI/列名/类型无破坏性变更
- [ ] 受影响模块负责人已通知并确认
- [ ] AOSP 框架改动已最小化；已评估非框架替代方案
- [ ] 若需要 ADR：ADR 已获批，且 Commit Message 中包含 ADR 引用

---

## 📚 参考文件

| 文件 | 内容 |
|---|---|
| [`references/coding-standards.md`](references/coding-standards.md) | 四（Java）、五（C）、六（C++）编码规范详细内容 |
| [`references/security-compatibility.md`](references/security-compatibility.md) | 七（安全）、八（兼容性）、九（检测流程）详细内容 |
| [`references/process-workflow.md`](references/process-workflow.md) | 十一（PR流程）、十二–十五（流程规范）详细内容 |
