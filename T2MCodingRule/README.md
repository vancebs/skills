# T2MCodingRule

## 功能简述

T2Mobile 公司编码规范与开发流程知识库。涵盖 Git Commit Message 规范、代码提交前检查要求、Code Review 流程与规范、Java / C / C++ 编码规范、安全编码规范、兼容性编码规范。Agent 加载本 skill 后，可回答所有与 T2Mobile 开发标准相关的问题，并在 code review、commit message 编写等任务中自动应用这些规范。

> 本 skill 为纯知识库，**无需任何配置**，加载即用。

---

## 详细功能描述

### 一、Git Commit Message 规范

#### 格式模板

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

#### 质量要求

- `* Solution` 必须具体描述实际技术改动，使读者无需查看代码即可理解变更核心
- 禁止使用无实质意义表述：如 "Fix code to meet customer's requirement"、"代码优化"
- 正确示例：`Set persist.vendor.usb.config as "none" to restore default USB mode after production flag is set.`

#### 涉及安全/兼容性变更时追加字段

```
* Security Check
<通过 / 不适用，注明原因>
* Compatibility Check
<通过 / 不适用，注明原因>
```

#### 涉及 ADR 时

变更涉及 AOSP 框架目录、新增系统服务或重大架构调整时，Commit Message 中必须包含已审批 ADR 文档引用。

---

### 二、代码提交前检查

`git push` 提交到 Gerrit 前，必须确保：

- 代码能**编译通过**，无错误或警告
- 本地已**验证**问题被解决或开发目的达成
- 不含**敏感信息**（密码、密钥、token、内网地址）
- **注释完整**、函数/变量命名规范
- 与需求文档/**Jira ID** 对齐
- 禁止上传大文件、二进制、敏感 PDF

---

### 三、Code Review 规范与流程

#### Reviewer 职责

- 代码**逻辑正确性**
- **风险点、边界条件**处理
- **兼容性、安全性、性能**影响
- **命名合理性**、冗余代码清理
- 符合编码规范（C/C++/Java）
- **注释充分、清晰**
- 对基线代码的修改遵守**最小改动原则**
- Commit Message `* Solution` 是否有实质技术描述

#### Review 要求

- 至少 **1 人** Review，核心模块需 **2 人**（通常为 TL 和 SPM）
- Review 通过后方可 merge

#### 静态分析要求

- 通过 **SonarQube** 检测（仅检测 patch 改动部分，Quality Gate 须为 **Passed**）
- 通过 XML 完整性检测

#### AI Code Review

Gerrit 提交后 AI Code Review 自动触发，结果以 Gerrit 评论形式发布。开发工程师必须对每条发现回复：
- **已修复**：说明修复方式，上传新 patch set
- **误报**：说明判断依据
- **可接受风险**：说明理由，需 STL 确认

未处理 AI Code Review 报告的 patch，STL 不得给出 Code Review +2。

#### Review 结论

- 全部通过：Code Review **+2**，允许合入
- 发现问题：Code Review **-1**，列出不符合规范条目，开发工程师修改后重新提交

---

### 四、Java 编码规范

#### 命名规范

| 类型 | 规则 |
|---|---|
| 包名 | 全小写，无下划线：`com.example.myapp` |
| 类名 | **大驼峰**：`ActivityManager` |
| 接口名 | **I + 大驼峰**：`IActivityManager` |
| 方法名 | **小驼峰**：`getUserInfo()` |
| 常量名 | **CONSTANT_CASE**：`TRANSPORT_TYPE_INVALID` |
| 非常量成员字段 | **m 前缀**：`mCacheDir` |
| 静态字段 | **s 前缀**：`sDefaultTimeout` |
| 测试类 | 被测类名 + `Test`：`ActivityManagerTest` |

#### 注释规范

- 修改代码时同步修改注释
- 新增类/接口注释列出目的和功能
- TODO 格式：`// TODO(xxx@t2mobile.com): 描述 who 与 why`
- 新增类命名加 `t2m` 前缀，文件放在 `vendor/t2m/` 目录
- 新特性代码用 Feature 开关控制

#### 排版规范

- 缩进：**4 个空格**；每行最多 **100 个字符**；方法超 **40 行**考虑拆分

#### 编码逻辑

- 不忽略异常；捕获具体异常类型（非通用 Exception）
- switch/case 不遗漏 break；if-else if 必须有 else
- 嵌套不超过 **3 层**；禁止硬编码魔鬼数字
- DB/IO 操作在 `finally` 中 `close()`
- 跨进程调用须做权限检查并处理 `RemoteException`

#### Log 规范

- 准确使用 `Log.v/d/i/w/e`；禁止在 log 中出现个人信息
- 禁止提交含冗余调试 log 的代码；禁止 `System.out` / `System.err`

---

### 五、C 编码规范

#### 文件命名

- 驼峰命名，长度 ≤ 48 字符
- 格式：`<SoftwareComponent>[_Cluster][_Function]<.h/.c>`

#### 数据类型命名

格式：`[DataTypeType]_[SoftwareComponentName_]<DataTypeName>_t`

| 前缀 | 含义 |
|---|---|
| `b` | 基本数据类型 |
| `s` | struct |
| `e` | enum |
| `a` | array |
| `p` | pointer |

- 宏命名全大写，格式：`<SoftwareComponents>_<MacroNames>`
- 枚举必须包含 MAX 值用于范围检查

#### 变量命名

- 全局变量格式：`<SoftwareComponent>[_Cluster/Functions]_<VariableDescription>[_DataCluster]`
- 局部变量格式：`[Cluster/Functions_]<VariableDescription>[_DataCluster]`
- 变量名长度 ≤ 64 字符，采用驼峰命名法

---

### 六、C++ 编码规范

#### 命名规范

| 类型 | 规则 |
|---|---|
| 类/结构/枚举 | **大驼峰**：`UrlTable` |
| 函数/方法 | **大驼峰**：`OpenFile()` |
| 变量 | **小驼峰**：`tableEntries` |
| 常量/枚举值 | `k` + 大驼峰：`kDaysInWeek` |
| 宏 | **全大写 + 下划线**：`MY_MACRO_THAT_SCARES` |
| 成员变量 | **下划线结尾**：`tableName_` |
| 全局变量 | `g_` 前缀：`g_TableName` |

#### 代码规范

- 优先使用 C++ 风格类型转换（`static_cast` 等）
- 所有头文件有 `#define` 防护
- 避免 RTTI（`dynamic_cast`/`typeid`）
- 禁止使用异常
- 合理使用 `const`；常量引用传参：`void Foo(const string& in)`

---

### 七、安全编码规范

- 禁止硬编码密码、密钥、token
- 输入验证：对所有外部数据（用户输入、网络、文件）做边界检查和类型验证
- SQL/命令注入防护：使用参数化查询，禁止字符串拼接
- 敏感数据不写入 log 和持久化存储
- 跨进程通信做权限校验
- 使用安全 API：避免 `strcpy`/`sprintf`，使用 `strncpy`/`snprintf`

---

### 八、兼容性编码规范

- 新增功能必须用 Feature 开关控制，打开/关闭均不影响原生逻辑
- 保持对原生代码最小改动；新文件放在 `vendor/t2m/` 仓库
- 修改 AOSP 框架目录、新增系统服务或重大架构调整须关联 ADR
- 向后兼容：API 变更须保留旧接口或提供迁移指南
