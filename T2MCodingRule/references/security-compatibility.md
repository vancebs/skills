# 安全编码 & 兼容性编码规范

> **来源：** T2MCodingRule skill 参考文件。查看安全编码要求、兼容性编码要求、检测流程触发条件时参考本文档。

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
- 禁止将密钥文件、证书等提交到代码仓

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
- 当框架改动确实不可避免时，必须在 Commit Message 中说明已评估的非框架替代方案及被否定的原

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
| 涉及密钥、证书、敏感配置的变更 | ✓ |
