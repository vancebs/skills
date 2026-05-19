# 流程规范（PR流程 / SDK升级 / 测试 / 发布 / 需求）

> **来源：** T2MCodingRule skill 参考文件。查看问题解决流程、SDK升级、软件发布等流程规范时参考本文档。

---

## 十一、问题解决流程（PR 流程）

### 11.1 角色说明

| 角色 | 职责 |
|---|---|
| VPM（Validation PM） | 分析 PR 优先级，确保 PR 按时关闭；是软件开发团队的客户，负责接受/拒绝交付 |
| SPM（Software PM） | 技术侧分析 PR，提供解决方案，确保 PR 按时交付；组织 SDK/AOSP 升级影响评估；负责收集客户交付要求，与客户协商内容、日期、到期日 |
| QPM（Quality PM） | 从终端用户测试获取 PR，组织与 SPM/VPM 的评审 |
| STL（SWD Team Leader） | 主导 PR 调查，验证 SWD 内部解决情况，集成负责人确认 patch 入官方版本 |
| SWD 工程师（SE） | 按 PR 解决计划调查和修复 bug，提交 patch，设置 PR 状态为 "Resolved" |
| INT 团队（SIE） | 集成和编译 SWD 提交的 patch，交付前执行基本内部验证，发送交付通知邮件 |
| VAL 工程师 | 提交 PR 到 Jira，验证已交付的 PR 是否正确解决 |
| CUST（客户） | 提交 PR 到 Jira 并指定给 SPM |

### 11.2 PR 完整状态流转（来自 PR流程.drawio）

```
Reporter 提交 PR → New
         ↓
SPM/STL 分配 → Assigned
         ↓
SW Engineer 判断是否是 Bug
    ├─ Yes (Not a bug?) → Argue（争议，反馈给 Reporter，Reporter 决定是否接受）
    │         ├─ Accept? Yes → Close（Reporter 直接关闭）
    │         └─ Accept? No → 重新 Investigate
    └─ No (是 Bug) → In Progress（调查中）
         ↓
    Commit patches → Committed
         ↓
    Verify with daily build
    ├─ Fail → 返回 In Progress（重新调查）
    └─ Pass → Resolve → Resolved
         ↓
    INT: deliver new version → Delivered
         ↓
    Reporter: Verify
    ├─ Pass → Is low frequency?
    │    ├─ No → Close → Closed
    │    └─ Yes → Monitor（监控）
    │              ↓
    │         Is 3 versions monitored?
    │         ├─ Yes → Close → Closed
    │         └─ No → 继续 Monitor
    └─ Fail (Refused) → 返回 SW Engineer 重新 Investigate
```

注：**任何状态都可以直接变更为 Postponed（延后）状态**。

| 状态 | 说明 |
|---|---|
| New | 新提交的问题 |
| Assigned | 已指派给 SW 工程师 |
| Argue | 工程师认为不是 Bug，提出异议，等 Reporter 决定是否接受 |
| In Progress | 正在调查 |
| Committed | 代码已提交，等待自测验证 |
| Resolved | SWD 工程师验证问题已解决（或标注 "Unable to self-test"） |
| Delivered | 集成团队确认 patch 在官方版本中 |
| Verified / Monitor | VAL 验证通过但低复现率，监控 3 个版本 |
| Closed | VAL/报告人确认已解决 |
| Refused | VAL/报告人确认未解决，退回原指定人重新调查 |
| Postponed | 推迟处理（任何阶段均可进入） |

### 11.3 详细流程步骤

1. **PR 提交**：VAL 工程师/QPM/客户在 Jira 中提交，选择正确的组件；VPM 和 SPM 分析并指派
2. **PR 评审**：VPM 和 SPM 每周至少评审一次所有 PR，更新优先级和描述；非软件问题通知 SPM 处理
3. **问题调查**：SPM 和 STL 主导，确保 PR 指派给正确的 SWD 工程师；提交的 patch 注释必须描述清楚（根本原因、错误原因、解决方案）
4. **SWD 验证**：COMMITTED 状态时，SWD 工程师在日常版本上验证，验证通过后设为 RESOLVED
5. **软件交付**：集成团队发布官方版本，所有已发布 PR 设为 DELIVERED
6. **软件验证**：报告人验证：通过→CLOSED；未通过→REFUSED；低复现率→MONITOR（3个版本后决定）
7. **PR 关闭**：由原始报告人关闭，或出现 CR 时由 VPM 关闭

### 11.4 客户 PR 特殊要求

- SPM 需给出明确的 end date（截止日期），需参考 STL 的技术建议并遵守 KPI 规则
- 所有 PR 每周至少检查和更新一

---

## 十二、SDK/平台升级操作规范

进行 AOSP 大版本升级或 Qualcomm BSP 升级时，按以下步骤执行：

1. **变更影响评估**：STL 组织对 API diff、Behavior Change 文档进行评审，输出影响范围清单
2. **编译验证**：升级后零警告编译（或已知警告已登记在案）
3. **静态分析**：通过 SonarQube 扫描，确认无新问题
4. **回归测试**：针对影响范围清单逐项执行，测试结果记录在 Jira
5. **兼容性签收**：VAL 工程师对受影响功能执行专项验证，通过后进入发布流

---

## 十三、软件测试管理规定（T2M-WI-RD-006）

### 13.1 主要角色

| 角色 | 职责 |
|---|---|
| VPM（软件验证项目经理） | 负责软件测试策略/计划制定，软件质量审核及出货版软件交付；组织问题报告分析会议；管理验证项目从计划阶段到产品市场发放 |
| Validation Team Leader | 组织测试用例维护更新，监控测试技术发展，按测试计划组织测试活动，审核测试结果 |
| VAL 工程师 | 执行测试，提交软件缺陷到 Jira，提交测试报告，跟进 PR 完整生命周期，验证并关闭 |
| VAL Automation Engineer | 开发自动化测试工具，构建自动化测试系统，维护自动化框架，执行自动化冒烟/AFM/稳定性测试 |

### 13.2 测试阶段

| 阶段 | 准入条件 | 输出 |
|---|---|---|
| **Organization（组织阶段）** | 项目 Kick off 且 requirement clarify 后 | 软件测试计划、测试用例 |
| **Stabilization（稳定化阶段）** | 收到稳定样品且软件 FC（Feature Complete）完成 | 软件测试周报、测试报告、软件缺陷报告（DR slide）、SW for FSR |
| **Maintenance（维护阶段）** | 软件 FSR（Final Software Release）后 | MR 测试报告、MR 软件 Google 认证 |

### 13.3 交付（Delivery）条件

- 所有测试条目按计划测试完成
- 获得 Google GMS certification 认证
- 没有 Block / Highest 级别的软件缺陷问题

### 13.4 测试用例管理流程（TestLink）

1. VPM 创建项目名称，Team Leader 制定测试策略和测试计划
2. 收到新版本后，在 TestLink 中创建版本，命名规则：`ProjectName_[Strategy]_ProjectInfo` 等
3. Test Engineer / Feature Owner 评审测试用例
4. 如需新增/删除/更新：维护项目库
5. 准备测试环境，Test Engineer 执行测试，执行状态报告给 VPM

### 13.5 软件缺陷跟踪

缺陷状态流转参见第十一章《问题解决流程》。所有缺陷在 Jira 系统中提交和管理

---

## 十四、软件发布流程（T2M-WI-RD-008）

### 14.1 进入条件

- 软件功能明确，或在 Jira 中提交 FRS 且 SDP 明确，意味着软件开发开始
- 来自 PM/VPM 的紧急软件修改请求（CRS/PR）已在 Jira 中提交并共享给软件团队

### 14.2 退出条件

- 软件产品存档并交付给 VPM
- 软件修改请求已完成，补丁已交付
- Jira 中没有正在进行的 FRS/CRS/PRS
- 项目已关闭

### 14.3 发布流程步骤

1. **估算工作量**：
   - 有任务清单时，SPM 与工程师估算工作量，召开软件交付会议（里程碑版本需 VPM/PM 参与）
   - 会议纪要明确下次交付中需要修正的正式 FRS/CRS/PR 清单及截止日期
   - 资源不足时，SPM 从 PM/VPM 获取任务优先级

2. **确定交付进度**：
   - 交付计划必须包含：交付到期日、任务列表、任务优先级
   - 有特殊要求时，交付计划需经主要参与者审查
   - 交付计划必须通知每个软件项目团队成员

3. **软件开发和 patch 提交**：
   - SE 根据优先级完成任务，高优先级任务优先
   - SE 提交并上传修补程序，**提交前必须审查 patch**
   - **patch 注释必须清楚描述**：对于 PRS，必须填写根本原因、错误原因、解决方案
   - 使用 patch 提交工具，信息自动记录到 Jira

4. **检查工作包**：
   - SE 确认所有 patch 已提交
   - SPM 根据任务清单检查整个工作包；有未完成任务时，调查延迟原因，估计完成工作量
   - 有未完成任务时，SPM 与 VPM/PM 讨论是否可接受；如不可接受，重新决定交付日期

5. **集成、编译和执行交付 Checklist**：
   - SIE 确认所有 patch 已提交，然后编译
   - 编译后执行 Delivery Checklist（主要功能测试用例列表，INT 团队编写，SPM 批准）
   - 软件更新后需重新测试
   - 发现错误时，SPM 与 VPM/PM 讨论是否可接受；如接受，错误应在下一版本修复

6. **交付前审批**：
   - 交付必须先经 SPM 批准，再经软件经理批准
   - SIE 可通过邮件将 Checklist 发送给 SPM 和 SW 经理审批（适用于正式版和迷你版）

7. **新软件交付和存档**：
   - INT 团队将软件 BIN 文件推送到 T2Download 服务器
   - 发送交付通知邮件前，INT 团队需下载并刷新软件版本，验证其可正常工作
   - 源代码和编译配置**必须 tag 到数据库**，以便需要时恢复相同环境

### 14.4 交付通知邮件必须包含

- 项目名称及软件版本号
- T2Download 中 bin 文件的地址
- 可用的 T2Download 版本
- 软件基础版本号 / 软件主版本号
- **软件更改列表**（修复的 FR/PR/CR 列表和修补程序）及发布说明
- Checklist 测试结果
- 软件命名规

---

## 十五、软件需求管理流程（T2M-WI-RD-009）

### 15.1 定义

| 术语 | 说明 |
|---|---|
| FR | Functional Requirement（功能要求） |
| CR | Change Request（更改要求） |
| REQ | Jira 中的需求数据库 |
| SPM | Software Project Manager（软件项目经理） |
| SPL | Software Project Leader |

### 15.2 FR/CR 管理流程

1. **FR 创建**：新项目启动阶段，SPM 根据继承的项目 FR、ID 卡、请求等在 Jira 系统中创建项目 FR
2. **FR 审查**：SWD FR 所有者和 VPM 通过 Jira 系统审查，可为任何 FR 添加注释
   - 确认：SWD FR 所有者接受并将状态改为"已分配"
   - 有问题：SWD FR 所有者或 VPM 可以拒绝该 FR
3. **CR 创建**：根据客户要求或内部/外部建议，SPM 随时在 Jira 中提交 CR
4. **CR 审核与克隆**：SPM 每周对 CR 列表进行总结审查，进行可行性分析和工作量评估
   - DR1 之前：如开发，SPM 将 CR 克隆到 Jira 的项目 FR（同平台项目一般均需实施）
   - DR1 之后：如有变更请求，则保留 CR
5. **FR/CR 开发、测试和关闭**：SWD 工程师根据 FR 开发软件；VAL 团队测试所有交付的软件；功能生效后，FR/CR 关闭
6. **需求变更管理**：项目开发阶段如有变更请求，请求者与 SPM 沟通对齐后，SPM 在 Jira 提交 CR，经历与 5.4 和 5.5 相同的过
