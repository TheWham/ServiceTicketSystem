# 错误AADSTS700003 - 在租户“TenantName<”>目录中找不到设备对象

## 概要

本文介绍如何解决尝试登录到集成到 Microsoft Entra ID 中的应用程序时发生的“AADSTS700003”错误。

## 症状

尝试登录到集成到 Microsoft Entra ID 中的应用程序时，会收到以下错误消息之一的“AADSTS700003”错误：

- > 在租户“TenantName<”>目录中找不到设备对象。
- > 你的组织已删除此设备。

## 原因

发生此问题的原因是设备对象在主租户上被删除。 删除设备后，“删除设备”活动类型将记录在 Microsoft Entra 审核日志[中](/zh-cn/entra/identity/monitoring-health/concept-audit-logs)。 在Microsoft Entra ID 中，可通过三种方式注册或加入用户设备：

- 已注册 Microsoft Entra
- 已建立 Microsoft Entra 联接
- 已建立 Microsoft Entra 混合联接

设备注册或加入会创建 [设备标识](/zh-cn/entra/identity/devices/overview)。 此设备标识用于使用 Microsoft Intune [的](/zh-cn/mem/endpoint-manager-overview)[基于设备的条件访问策略](/zh-cn/entra/identity/conditional-access/concept-conditional-access-grant)和移动设备管理等方案。 收到AADSTS700003错误时，在租户中找不到设备对象。

## 解决方案

请让主租户管理员确定何时以及为什么删除设备对象。 然后，根据设备注册/联接类型执行相应的作，如下表所示：

| 设备加入类型 | 操作 |
| --- | --- |
| 已注册 Microsoft Entra | 对于 Windows 10/11 Microsoft Entra 注册的设备，请转到**“设置**>> 选择屏幕上的工作或学校帐户。 选择“断开连接**”**以断开设备的连接。 然后，再次将设备注册到 Microsoft Entra ID。  对于 iOS 和 Android，可以使用 Microsoft Authenticator 应用程序并选择“>**注销设备”。** 然后，再次将设备注册到 Microsoft Entra ID。  对于 macOS，可使用 Microsoft Intune 公司门户应用程序从管理中取消注册设备，并删除任何注册。 然后，再次将设备注册到 Microsoft Entra ID。   有关详细信息，请参阅 [Microsoft Entra 注册常见问题解答](/zh-cn/entra/identity/devices/faq#how-do-i-remove-a-microsoft-entra-registered-state-for-a-device-locally)。 |
| 已建立 Microsoft Entra 联接 | 在 Windows 设备上打开具有管理权限的 PowerShell 控制台，然后运行 `dsregcmd /forcerecovery` 该命令。 选择 **“登录** ”以使用Microsoft Entra ID 帐户登录。 |
| 已建立 Microsoft Entra 混合联接 | 在 Windows 设备上打开具有管理权限的 PowerShell 控制台，然后运行 `dsregcmd /leave` 该命令。 然后，重新启动设备并使用域凭据登录到设备。 |

## 详细信息

有关身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/azure/active-directory/develop/reference-error-codes)。

若要调查单个错误，请转到 <https://login.microsoftonline.com/error>。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-aadsts700003-device-object-not-found)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
