---
name: T2MCodingRule
description: "T2Mobile公司编码规范与开发流程知识库。当用户询问T2Mobile编码规范、代码风格、命名规则、注释要求、排版规范、git commit message格式、code review流程与规范、问题解决流程（PR流程）、安全编码要求、兼容性编码要求等任何与T2Mobile开发标准相关的问题时，调用此skill。触发词包括：编码规范、命名规范、注释规范、代码风格、commit message、code review、PR流程、问题解决流程、安全规范、兼容性规范、T2Mobile规范等。"
---

# T2Mobile 编码规范与开发流程知识库

本skill涵盖T2Mobile公司适用于C/C++/Java开发的完整编码规范、Git提交规范、Code Review规范与流程、问题解决流程（PR流程）、安全编码规范、兼容性编码规范等。

---

## 📖 快速导航（Quick Lookup Guide）

**不确定看哪一节？请参考下表直接跳转：**

| 我需要了解… | 查看章节 |
|---|---|
| 如何写 git commit message | [一、Git Commit Message 规范](#一git-commit-message-规范) |
| 提交代码前要检查什么 | [二、代码提交前检查](#二代码提交前检查) |
| Code Review 的流程和要求 | [三、Code Review 规范与流程](#三code-review-规范与流程) |
| Java 代码风格、命名、注释 | [四、Java 编码规范](#四java-编码规范) |
| C 代码风格、命名、注释 | [五、C 编码规范](#五c-编码规范) |
| C++ 代码风格、命名、注释 | [六、C++ 编码规范](#六c-编码规范) |
| 安全编码要求（权限、加密、日志） | [七、安全编码规范](#七安全编码规范) |
| 兼容性编码要求（API、HAL、AIDL） | [八、兼容性编码规范](#八兼容性编码规范) |
| 什么时候需要做安全/兼容性检测 | [九、安全/兼容性检测流程](#九安全兼容性检测流程触发条件) |
| 架构变更需要写 ADR | [十、架构决策记录（ADR）](#十架构决策记录adr) |
| 发现问题如何走 PR 流程 | [十一、问题解决流程（PR 流程）](#十一问题解决流程pr-流程) |
| SDK/平台升级规范 | [十二、SDK/平台升级操作规范](#十二sdk平台升级操作规范) |
| 测试管理要求 | [十三、软件测试管理规定](#十三软件测试管理规定t2m-wi-rd-006) |
| 软件发布流程 | [十四、软件发布流程](#十四软件发布流程t2m-wi-rd-008) |
| 需求管理流程 | [十五、软件需求管理流程](#十五软件需求管理流程t2m-wi-rd-009) |
| 提交前综合自查清单 | [十六、提交前综合自查清单](#十六提交前综合自查清单) |

---

## ⚡ 常见场景速查

### 场景 A — 提交一个 Bug 修复
**步骤：**
1. 检查代码是否符合对应语言的编码规范（Java → 四，C → 五，C++ → 六）
2. 检查是否涉及安全或兼容性变更 → 若是，参考七/八/九
3. 填写 Commit Message（格式见一，必须关联 Jira ID）
4. 勾选 [提交前综合自查清单（十六）]
5. 创建 PR，@相关 Reviewer，遵守 Code Review 流程（三）

### 场景 B — Code Review 一个 PR
**检查清单：**
- [ ] Commit Message 格式正确（见一）
- [ ] 代码符合语言编码规范（Java/C/C++）
- [ ] 无硬编码密码/token/内网地址
- [ ] 涉及安全变更时，按七检查权限、日志、加密
- [ ] 涉及兼容性变更时，按八检查 API/HAL/AIDL 向后兼容
- [ ] Review 结论符合三中的标准（必须明确 Approved/Needs Changes）

### 场景 C — 发现一个线上问题
**步骤：** 按十一（问题解决流程）走完整 PR 流程：
1. 问题登记（Jira 创建 Bug，填写影响范围）
2. 根因分析（RCA 文档）
3. 修复方案 + 代码 Review
4. 测试验证（参考十三）
5. 发布（参考十四）
6. 回顾（Postmortem）

### 场景 D — 判断是否需要 ADR
参见十（架构决策记录）。需要 ADR 的典型情况：
- 引入新的第三方框架 / SDK
- 修改模块间接口协议
- 变更数据库 schema 或 ContentProvider 结构
- 安全策略重大变更

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

若变更涉及对 AOSP 框架目录的改动、新增系统服务、或重大架构调整，Commit Message 中必须包含已审批 ADR 文档的引用。

---

## 二、代码提交前检查

开发者在执行 `git push` 提交到 Gerrit 之前，必须确保：

- 代码能**编译通过**，无错误或警告（或警告已被允许）
- 本地已**验证**问题被解决或者开发目的达成
- 不包含**敏感信息**（密码、密钥、token、内网地址）
- **注释完整**、函数/变量命名规范
- 与需求文档/**Jira ID** 对齐
- 禁止上传大文件、二进制、敏感 PDF

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
- 发现问题：Code Review -1，在评论中列出不符合的规范条目，开发工程师修改后重新提交

---

## 四、Java 编码规范

### 4.1 命名规范

| 类型 | 规则 |
|---|---|
| 标识符 | 仅使用 ASCII 字母和数字；禁止拼音缩写；禁止非标准英文缩写 |
| 包名 | 全小写，连续单词直接连接，无下划线：`com.example.deepseek` |
| 类名 | **大驼峰**：`ActivityManager` |
| 接口名 | **I + 大驼峰**：`IActivityManager` |
| 方法名 | **小驼峰**：`getUserInfo()`；getter 以 `get`/`is`/`has`/`can` 前缀，setter 以 `set` 前缀 |
| 参数名 | **小驼峰** |
| 常量名 | **CONSTANT_CASE**（全大写+下划线）：`TRANSPORT_TYPE_INVALID` |
| 非常量成员 | **小驼峰** |
| 局部变量 | **小驼峰**；除循环变量外不取单字符命名；输入流加 `in` 前缀，输出流加 `out` 前缀 |
| 非公共非静态字段 | **m 前缀**：`mCacheDir` |
| 静态字段 | **s 前缀**：`sDefaultTimeout` |
| 测试类 | 以被测类名开头，以 `Test` 结尾：`ActivityManagerTest` |
| 集合类字段 | 名词复数：`ArrayList<String> updatedComponents` |

### 4.2 注释规范

- 修改代码时，**同步修改相应注释**，删除不再有用的注释
- 重载父类方法必须有 `@Override` 声明
- 新增类或接口注释必须列出**目的和功能**
- 新增变量，注释放在变量**上方**
- TODO 格式：`// TODO(xxx@t2mobile.com): 描述需要做的事，说明 who 与 why`
- 弃用注释用 `@Deprecated` 标记，说明替代方案
- 删除 AOSP 代码用 `/* ... */` 注释掉，保留可读性
- 新增 AOSP 代码时，新功能分离为独立函数或类
- 新文件头模板：

```java
/********************************************************************************
** Copyright (C), 2020-2025, T2Mobile
** VENDOR_EDIT, All rights reserved.
**
** File: - xxx.java
** Description:
** xxx
**
** --------------------------------- Revision History: --------------------------
** <author> <date> <version> <desc>
** ------------------------------------------------------------------------------
** xxx@t2mobile.com 2024-06-15 v1 add init version.
********************************************************************************/
```

- 新增类命名加 `t2m` 前缀，文件放在 `vendor/t2m/` 下对应目录
- 新特性代码须用 Feature 开关控制：

```java
if (Features.isSupport(Features.TCL_FEATURE_YOUR_FEATURE_NAME)) {
    // implement your feature here.
}
```

### 4.3 排版规范

- 缩进：**4个空格**
- 每行最多 **100 个字符**
- 每行**只写一条语句**
- 方法超过 **40 行**时，考虑拆分
- 换行：逗号后换行；运算符前换行
- 大括号：左括号前不换行，左括号后换行，右括号前换行
- 关键字（if/for/while）与后面括号间加**空格**
- 二元运算符两边加**空格**；单目运算符（`!`, `~`, `++`, `--`）前后不加空格
- 方法名和左括号间**无空格**
- 逗号、冒号、分号后加空格
- 强制类型转换后加空格

### 4.4 编码逻辑

- **不要忽略异常**：catch 块必须处理，不能为空
- **不要捕获通用异常 Exception**：捕获具体异常类型
- **不要使用 finalizers**
- **不要使用通配符导入**：`import foo.Bar;` 而非 `import foo.*;`
- switch/case **不要遗漏 break**；若故意不加，必须注释；必须有 **default 分支**
- if/for/do/while/switch 即使只有一条语句也要加 **大括号 {}**
- if-else if 最后必须有 **else**
- 嵌套语句不超过 **3 层**，建议使用卫语句
- 避免**硬编码**（魔鬼数字），用有意义的常量或枚举替代
- 参数须做**有效性检查**
- DB/IO 操作必须在 `finally` 中 `close()`
- 跨进程调用须做**权限检查**，并处理 `RemoteException`
- `equals` 比较时，常量放左边：`DEFAULT_PACKAGE_NAME.equals(packageName)`

### 4.5 Log 规范

- Log 等级要准确：使用 `Log.v/d/i/w/e`，异常捕获用 `Log.e`
- **禁止**Log 中出现个人信息（姓名、工号、邮箱）
- **禁止**提交代码中含冗余调试 log
- **禁止**使用 `System.out` / `System.err`
- debug 信息用 `DEBUG` 开关控制

### 4.6 代码解耦

- 新加功能必须用**功能 Feature 开关**控制，打开/关闭均不影响原生逻辑
- 保持对**原生代码最小改动**，新文件建议放在 `vendor/t2m/` 仓库
- 在原生文件中，只修改**插桩点**，调用相关 API

---

## 五、C 编码规范

### 5.1 文件命名

- 文件名采用**驼峰命名法**，长度不超过 **48 个字符**
- 一个文件只能归属于**一个软件组件**
- 文件名结构：`<SoftwareComponent>[_Cluster][_Function]<.h/.c>`
  - Cluster 类型：`Lcfg`（链接配置）、`Cfg`（编译配置）、`PBcfg`（后编译配置）
  - Function：`Type`（数据类型定义）或子功能名

**`.c` 文件必须包含：**
`[FILE DESCRIPTIONS]`, `[HEADER FILES]`, `[MACRO DEFINITION]`, `[TYPEDEF DEFINITION]`, `[LOCAL DATA DECLARATION]`, `[GLOBAL DATA DECLARATION]`, `[LOCAL FUNCTION DECLARATION]`, `[GLOBAL FUNCTION DECLARATION]`, `[LOCAL DATA]`, `[GLOBAL DATA]`, `[LOCAL FUNCTION]`, `[GLOBAL FUNCTION]`

**`.h` 文件必须包含：**
`[FILE DESCRIPTIONS]`, `[HEADER FILES]`, `[MACRO DEFINITION]`, `[TYPEDEF DEFINITION]`, `[LOCAL DATA DEFINITION]`, `[LOCAL FUNCTION DECLARATION]`

### 5.2 数据类型命名

格式：`[DataTypeType]_[SoftwareComponentName_]<DataTypeName>_t`

DataTypeType 前缀：
- `b`：基本数据类型
- `s`：struct
- `e`：enum
- `a`：array
- `p`：pointer

**枚举类型：**
```c
enum e_Ota_EraseStatus_t {
    OTA_ERASESTATUS_IDLE = 0,
    OTA_ERASESTATUS_PENDING,
    OTA_ERASESTATUS_ERROR,
    OTA_ERASESTATUS_FINISH,
    OTA_ERASESTATUS_MAX  // 枚举必须包含MAX值用于范围检查
};
```

**宏命名：**
- 全大写，单词间用下划线分隔
- 格式：`<SoftwareComponents>_<MacroNames>`
- 示例：`DCM_FUNCTIONAL_TYPE`, `AID_SYSTEM`

### 5.3 变量命名

**全局变量**格式：`<SoftwareComponent/FileName>[_Cluster/Functions]_<VariableDescription>[_DataCluster]`

变量类型后缀（DataCluster）：
| 后缀 | 含义 | 后缀 | 含义 |
|---|---|---|---|
| `_p` | 指针 | `_st` | 结构体变量 |
| `_pst` | 指向结构体的指针 | `_u8/u16/u32` | 无符号8/16/32位 |
| `_pcst` | 指向常量结构体的指针 | `_s8/s16/s32` | 有符号8/16/32位 |
| `_pu8/pu16/pu32` | 指向无符号数据的指针 | `_b` | 布尔 |
| `_a` | 数组 | `_f32/f64` | 浮点 |

**局部变量**格式：`[Cluster/Functions_]<VariableDescription>[_DataCluster]`

规则：
- 变量命名不超过 **64 个字符**
- 采用**驼峰命名法**
- 仅在文件内部使用的变量定义为**静态变量**
- 跨文件使用的变量在 `.h` 中声明，在 `.c` 中定义

### 5.4 函数命名

格式：`<SoftwareComponent/FileName>[_Cluster]_<FunctionDescription>`
- 函数名不超过 **64 个字符**
- 仅在一个 `.c` 文件内使用的函数定义为 **static**
- 参数采用**小驼峰**命名
- 私有函数用 `Prv` 标识：`Dcm_Prv_SetNonDefaultSesCtrlType()`

### 5.5 排版规范

- 缩进：**4个空格**
- 每行不超过 **80 字符**
- 每行只写**一条语句**
- C 语言大括号**另起一行**
- 条件编译 `#if` 放**行首**，不缩进
- 空格规则同 C++（见下文）

### 5.6 编码逻辑规则

- switch/case 不遗漏 break；必须有 default 分支
- if/for/do/while/switch 即使一条语句也加 **{}**
- 避免**硬编码**（魔鬼数字）
- 不使用难懂的高技巧语句（如 `*p_counter++ += 1`）
- **头文件防重复包含**：

```c
#ifndef MY_CLASS_H
#define MY_CLASS_H
// 真正的头文件内容
#endif // MY_CLASS_H
```

- `sizeof` 操作数不含有副作用的表达式
- 循环计数器不用浮点型
- **禁止递归调用**
- 非空返回值的函数返回值**必须被使用**
- 不使用变长数组
- 自动变量使用前**必须赋值**
- 数组不应被部分初始化
- 避免**数组越界**，使用前判断范围
- 避免**空指针操作**，使用前判断非空
- `malloc` 后**立即检查**是否成功，并立即初始化
- 参数做**有效性检查**
- **禁止** return 返回指向栈内存的指针
- 动态申请的内存使用完后**及时释放**

---

## 六、C++ 编码规范

### 6.1 变量命名

- 局部变量：**小驼峰** (`cameraId`, `maxResolutionWidth`) 或 全小写+下划线 (`device_name`)
- 全局变量：**g + 大驼峰** (`gDeviceCpuCoreCount`) 或 `g_` + 下划线分隔 (`g_screen_refresh_rate`)
- 成员变量：**m + 大驼峰** (`mDisableClientCompositionCache`) 或 `m_` + 下划线 (`m_items`)
- 静态变量：**s + 大驼峰** (`sStr64`) 或 `s_` + 下划线 (`s_count`)
- **修改已有模块时，保持与原有模块风格一致；新模块建议采用小驼峰风格**

### 6.2 常量命名

- `#define` 宏：全大写+下划线：`AID_SYSTEM`，附注释说明用途
- `const/constexpr`：小驼峰，或 `k` 前缀（`kDex2oat32Path`），或全大写+下划线
- 枚举常量：全大写+下划线，或大驼峰，或 `k` 前缀

### 6.3 函数命名

- C++ 函数：**小驼峰**第一字母小写（`getServiceName()`）
- C 风格函数：全小写+下划线（`open_account()`, `reset_cards()`）
- getter/setter：`get`/`set`/`is`/`has`/`can` 前缀
- 互斥操作用反义词组：`add/remove`, `open/close`, `lock/unlock`, `start/stop` 等
- 参数：**小驼峰**

### 6.4 类、结构体、模板、联合体命名

- 大驼峰：`UrlTable`, `UrlTableTester`, `UrlTableProperties`

### 6.5 命名空间

- 全小写，基于工程名：`namespace frameworks {}`

### 6.6 文件名

- C++ 常用：每个单词首字母大写（`WindowInfosListenerInvoker.cpp`）
- C 风格：全小写+下划线（`installd_constants.h`）

### 6.7 注释规范（AOSP 代码修改）

增删改均用 `// #ifdef VENDOR_EDIT` 和 `#endif /* VENDOR_EDIT */` 标记：

```cpp
// 增加
void googleFuntion() {
    doSomething();
#ifdef VENDOR_EDIT
    doCustomizedFunction();
#endif /* VENDOR_EDIT */
}

// 修改
void googleFuntion() {
#ifndef VENDOR_EDIT
    doOtherThings();
#else
    doCustomizedFunction();
#endif /* VENDOR_EDIT */
}

// 删除
void googleFuntion() {
#ifndef VENDOR_EDIT
    doOtherThings();
#endif /* VENDOR_EDIT */
}
```

### 6.8 新增函数注释（Doxygen 格式）

```cpp
/**
@brief 函数功能简述
@param[in] un32_decoderID 操作的解码设备 ID
@param[out] un64_stc STC 值，单位 tick
@return FPI_ERROR_SUCCESS->正确, FPI_ERROR_FAIL->错误
*/
fpi_error fpp_decoder_get_stc(uint32_t u32_decoderId, uint64_t *un64_stc);
```

### 6.9 新增文件头注释

```cpp
/*************************************************
Copyright (C), 1981-2025, T2Mobile Co., Ltd.
@file: // 文件名
@brief: // 文件主要功能及与其他模块的关系
@author: // 作者
@date: // 创建日期
@version: // 版本
@history: // 修改历史表
*************************************************/
```

### 6.10 排版规范（与C规范一致）

- 缩进：**4个空格**
- 每行不超过 **80 字符**
- C++ 大括号**不另起一行**（左括号同行）
- 命名空间内容**不缩进**
- 条件编译 `#if` 放**行首**，不缩进
- 空格：双目运算符两边加空格；单目运算符前后不加空格；`->` 和 `.` 前后不加空格；模板 `<>` 内不加空格
- 不允许嵌套注释；`//` 行末不允许用 `\` 拼接下一行

### 6.11 编码逻辑规则（与C规范一致，附加）

- 函数尽量精简，**100行以内**
- 内联函数只在**小于10行**时才内联
- if/for/do/while/switch 即使一条语句也加 **{}**
- 避免硬编码；头文件防重复包含
- 避免数组越界、空指针操作
- `malloc` 后检查成功；使用完后**及时释放**
- 禁止递归调用
- 日志：提交代码不含冗余调试信息；不允许在循环体内用高频率打印；打印格式：前缀信息（时间|级别|模块名|线程PID）+ `func=函数名, 变量名=值`

---

## 七、安全编码规范

### 7.1 最小权限原则

- 只申请完成功能**必需**的最少权限；每条权限声明必须注明原因和使用位置
- `AndroidManifest.xml` 中每条 `<uses-permission>` 必须有对应代码使用点，不得存在未使用权限
- 危险权限运行时先检查再使用

| 高权限方案（禁止） | 低权限替代（推荐） |
|---|---|
| `READ_PHONE_STATE` 获取设备ID | `Settings.Secure.ANDROID_ID` |
| `ACCESS_FINE_LOCATION` | `ACCESS_COARSE_LOCATION`（精度足够时） |
| `WRITE_EXTERNAL_STORAGE` | Scoped Storage / MediaStore |

- 自定义权限必须指定合适 `protectionLevel`，敏感接口不得设为 `normal`

### 7.2 Android 组件安全

- 所有 `exported=true` 的组件必须设置 `android:permission`
- ContentProvider 读写权限分别声明（`android:readPermission` + `android:writePermission`）
- 涉及敏感操作的 Intent 通信必须使用**显式 Intent**，禁止通过隐式 Intent 传递支付、认证等敏感数据

### 7.3 Binder/AIDL 接口安全

- 系统服务接口实现**第一行**必须调用权限检查：

```java
mContext.enforceCallingOrSelfPermission(
    "com.t2mobile.pos.permission.PAYMENT_OPERATION",
    "doSensitiveOperation requires PAYMENT_OPERATION permission");
```

- 敏感接口加 UID 双重验证
- **禁止** `checkCallingPermission` 后忽略返回值，或权限不足时只打 log 继续执行

### 7.4 VSDK Framework API 安全

- VSDK 权限必须在 framework 系统层声明，不由第三方 APP 自行声明
- 每个通过 JAR 暴露的接口，Binder 实现**第一行**必须有 `enforceCallingOrSelfPermission`
- JAR stub 必须用 `@RequiresPermission` 注解标注所需权限

### 7.5 Linux 原生程序安全

- 原生程序不得以 root 身份长期运行，启动后立即**降权**（`setgid`/`setuid`），降权失败必须退出
- init rc 中始终使用 `user` 和 `group` 指令，且只声明必要的 capabilities
- 对安全敏感的守护进程，使用 `libminijail` 启用 **seccomp** 过滤
- 每个原生服务必须定义**专属 SELinux 域**，禁止复用通用域
- 禁止用 `audit2allow` 批量转换 AVC denial
- 数据文件权限设为 **0600**，禁止 group/other 访问
- 临时文件用 `mkstemp()` 创建后立即 `unlink()`
- 禁止在 `/sdcard`、`/tmp` 等全局可写目录存储敏感数据
- Binder/Socket 接口实现中验证调用方 UID/PID
- 所有外部输入进行**边界校验**；使用 `strlcpy`/`strlcat` 防止缓冲区溢出；禁止用户输入直接作为格式字符串

### 7.6 数据安全

- **禁止硬编码**密码、密钥、证书、token 或内网地址
- 敏感数据使用 Android Keystore 或硬件安全模块存储
- 日志不含敏感信息明文；生产版本禁用包含敏感数据的日志
- 禁止将密钥文件、证书等提交到代码仓库

---

## 八、兼容性编码规范

### 8.1 Android API 兼容性

- **禁止**在新代码中使用已标注 `@Deprecated` 的 API
- 升级 `compileSdkVersion` 时，必须全面排查并替换 deprecated API
- 建议保留版本适配注释说明替换原因
- `targetSdkVersion` 升级前，必须在 Jira/Gerrit 中列出所有 Behavior Changes 并逐项确认
- **禁止** APK 通过反射访问 `@hide` API；系统应用若必须使用，必须在注释和 Gerrit commit 中说明

### 8.2 HAL 接口（HIDL/AIDL HAL）

- **禁止**修改已发布版本中的现有方法签名
- **禁止**删除已发布版本中的任何方法或枚举值
- 新增方法/枚举值必须以**新版本号**（minor version bump）发布
- HAL 实现升级后，必须通过 VTS 验证

### 8.3 系统服务 AIDL 接口

- 可以新增方法（追加到接口末尾）
- **禁止**修改现有方法的参数和返回类型
- **禁止**删除现有方法
- Parcelable 新增字段必须有**默认值**
- 接口变更前必须通知所有已知调用方模块负责人确认

### 8.4 ContentProvider & 广播

- URI 路径、列名、数据类型一旦对外发布，不得在不通知调用方的情况下变更或删除
- 自定义广播的 Action 字符串、Extra 键名和类型一旦对外发布，不得单方面变更

### 8.5 AOSP 框架改动最小化

- 对 `frameworks/base`、`frameworks/native` 等核心框架目录的改动**必须最小化**
- 在实现任何需要修改框架的功能之前，必须评估**非框架替代方案**
- 常见替代方案：将功能实现为独立 vendor 服务；通过 AIDL/Binder 调用 vendor 服务；使用资源 overlay、HAL、vendor 服务等扩展机制
- 当框架改动确实不可避免时，必须在 Commit Message 中说明已评估的非框架替代方案及被否定的原因

---

## 九、安全/兼容性检测流程（触发条件）

以下类型变更必须经过额外检查：

| 变更类型 | 触发安全检查 | 触发兼容性检查 |
|---|---|---|
| 新增或修改 `AndroidManifest.xml` 权限声明 | ✓ | |
| 新增或修改 `exported=true` 的组件 | ✓ | |
| 新增或修改系统服务/Binder/AIDL 接口 | ✓ | ✓ |
| 新增或修改 HAL 接口（HIDL/AIDL HAL） | | ✓ |
| `targetSdkVersion`/`compileSdkVersion` 变更 | | ✓ |
| AOSP/Qualcomm BSP 大版本升级 | ✓ | ✓ |
| 新增或修改 ContentProvider/广播接口 | ✓ | ✓ |
| 涉及密钥、证书、敏感配置的变更 | ✓ | |

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
5. 实施 patch 的 Commit Message 中必须包含已审批 ADR 的引用

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
- 所有 PR 每周至少检查和更新一次

---

## 十二、SDK/平台升级操作规范

进行 AOSP 大版本升级或 Qualcomm BSP 升级时，按以下步骤执行：

1. **变更影响评估**：STL 组织对 API diff、Behavior Change 文档进行评审，输出影响范围清单
2. **编译验证**：升级后零警告编译（或已知警告已登记在案）
3. **静态分析**：通过 SonarQube 扫描，确认无新问题
4. **回归测试**：针对影响范围清单逐项执行，测试结果记录在 Jira
5. **兼容性签收**：VAL 工程师对受影响功能执行专项验证，通过后进入发布流程

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

缺陷状态流转参见第十一章《问题解决流程》。所有缺陷在 Jira 系统中提交和管理。

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
- 软件命名规则

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
6. **需求变更管理**：项目开发阶段如有变更请求，请求者与 SPM 沟通对齐后，SPM 在 Jira 提交 CR，经历与 5.4 和 5.5 相同的过程

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
