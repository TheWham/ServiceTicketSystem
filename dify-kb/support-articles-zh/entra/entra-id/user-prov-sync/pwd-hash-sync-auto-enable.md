# Microsoft Entra Connect 直通身份验证期间自动启用密码哈希同步

## 概要

本文可帮助你修复Microsoft Entra 连接器中自动启用密码哈希同步的问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 4051623

以下版本的 Microsoft Entra Connect 存在影响 **更改用户登录** 任务的问题：

- 1.1.557.0
- 1.1.558.0
- 1.1.561.0
- 1.1.614.0

这些问题会影响不想使用密码哈希同步的直通身份验证用户。

Microsoft Entra Connect 版本 1.1.644.0 [中](/zh-cn/azure/active-directory/connect/active-directory-aadconnect-version-history)修复了这些问题。

## 问题 1：当用户登录方法设置为直通身份验证时启用密码同步

### 方案 1

- 已有一个Microsoft Entra Connect 部署，该部署同时禁用了密码同步和直通身份验证。
- 使用 **更改用户登录** 任务启用直通身份验证后，会自动启用密码哈希同步。

### 方案 2

- 现有Microsoft已启用密码同步和直通身份验证的 Entra Connect 部署。
- 使用**“更改用户登录”任务启用或禁用**无缝单一登录****选项后，会自动启用密码哈希同步。

### 有关此问题的背景信息

- 在Microsoft Entra Connect 版本 1.1.557.0 之前，密码同步是启用直通身份验证的先决条件。 因此，启用直通身份验证时启用了密码同步。
- 由于直通身份验证不再需要密码同步，因此我们在 Microsoft Entra Connect 版本 1.1.557.0 中更改了此过程，以便在安装 Microsoft Entra Connect 期间启用直通身份验证时，它不会启用密码同步。
- 但是，相同的更改未应用于 **“更改用户登录** ”任务。 如果使用任务将直通身份验证启用到现有Microsoft Entra Connect 部署，则会自动启用密码同步。 此问题已在 Microsoft Entra Connect 版本 1.1.644.0 [中](/zh-cn/azure/active-directory/connect/active-directory-aadconnect-version-history)修复，以确保使用**更改用户登录**任务启用直通身份验证时密码哈希同步保持禁用状态。

## 问题 2：如果用户登录方法设置为直通身份验证，则有关禁用密码同步的错误提示

- 现有Microsoft已启用密码同步并禁用直通身份验证的 Entra Connect 部署。
- 使用 **更改用户登录** 任务启用直通身份验证后，密码哈希同步将保持启用状态。

### 有关此问题的背景信息

根据设计，如果启用了密码哈希同步，将用户登录任务更改为任何其他选项不会禁用密码哈希同步。 此问题已在 Microsoft Entra Connect 版本 1.1.644.0 [中](/zh-cn/azure/active-directory/connect/active-directory-aadconnect-version-history)修复，以防止显示提示窗口指出密码哈希同步已禁用。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 运行Microsoft Entra Connect，然后选择“ **查看当前配置**”。 在详细信息窗格中，检查**是否在租户上启用了**密码同步****。

   ![屏幕截图显示已启用密码同步状态。](media/pwd-hash-sync-auto-enable/password-synchronization.png)
2. **禁用密码同步**功能。 为此，请按照下列步骤进行操作：

   1. 运行Microsoft Entra Connect，然后选择“ **配置**”。
   2. **选择“自定义同步选项”任务**。
   3. 在 **“可选功能** ”页上，清除 **“密码同步** 功能”复选框。
   4. 完成向导。

（可选）如果要清除已同步到 Microsoft Entra ID 的密码哈希，请执行以下步骤：

1. 请确保**在租户上禁用**密码写回**功能**。 为此，请执行以下步骤：

   1. 运行Microsoft Entra Connect，然后选择“ **配置**”。
   2. **选择“自定义同步选项”任务**。
   3. 在 **“可选功能** ”页上，清除 **“密码写回** 功能”复选框。
   4. 完成向导。
2. 使用 [Reset-MgUserAuthenticationMethodPassword](/zh-cn/powershell/module/microsoft.graph.identity.signins/reset-mguserauthenticationmethodpassword) cmdlet 为所有受影响的用户设置随机密码。 必须为每个用户运行此 cmdlet 五次，因为 Microsoft Entra ID 将最后四个密码哈希存储在密码哈希历史记录中。

   注意

   如果 cmdlet 不适用于联合域用户，则可能需要暂时将用户的 UPN 更改为非联合域，然后运行 cmdlet 来设置随机密码。 之后，将用户的 UPN 还原到原始状态。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/pwd-hash-sync-auto-enable)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
