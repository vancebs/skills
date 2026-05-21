# 编码规范详细说明（Java / C / C++）

> **来源：** T2MCodingRule skill 参考文件。查看 Java、C、C++ 语言编码规范时参考本文档。

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

### 1.6 非正常路径处理（Commit Message）

当收到的 commit message 存在以下情况时，按以下规则处理，**不得跳过或自行修改**：

| 情况 | 处理规则 |
|---|---|
| commit message 为空 | 所有字段标记 `[🟠 ERROR]`，结果 FAIL |
| 仅有首行，无正文 | CM-4 ~ CM-7 均标记 `[🟠 ERROR]` |
| 多个 Issue Key（首行含多个 `[X-123] [Y-456]`）| 取第一个 Issue Key 验证，其余作为 `[🔵 INFO]` 附加信息 |
| Solution / Test Steps / Test Result 字段存在但内容为空行 | 与"字段缺失"等同，标记 `[🟠 ERROR]` |
| commit message 使用非英文（如中文）书写 | 不违规；但 Issue Key 格式仍须符合正则 `^\[?[A-Z0-9]+-\d+\]?` |
| 第三方 / vendor 提交（commit message 不符合 T2Mobile 格式）| 标记 `[🔵 INFO]`："疑似第三方提交，Commit Message 规范不适用，请人工确认" |
| 已合并（`status: MERGED`）或已废弃（`status: ABANDONED`）的变更 | 仍按规范审查；结论仅供参考（不影响已合入代码）

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
- 动态申请的内存使用完后**及时释放*

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
- 日志：提交代码不含冗余调试信息；不允许在循环体内用高频率打印；打印格式：前缀信息（时间|级别|模块名|线程PID）+ `func=函数名, 变量名=值
