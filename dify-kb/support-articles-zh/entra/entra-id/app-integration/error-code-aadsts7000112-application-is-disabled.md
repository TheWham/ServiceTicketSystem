# 错误AADSTS7000112 - 应用程序已禁用

## 概要

本文介绍如何解决 `AADSTS7000112` 尝试登录到可与 Microsoft Entra ID 一起使用的应用程序时发生的错误。

## 现象

尝试登录到集成到 Microsoft Entra ID 中的 Azure 应用程序时，会收到以下 `AADSTS7000112` 错误消息：

> 应用程序“<appIdentifier>”（<appName>）已禁用。

## 原因

在资源租户上禁用服务主体对象。

## 解决方案

与资源租户所有者协作，确定服务主体对象被禁用的原因。 然后，使用下表执行相应的操作。

| 场景 | 操作 |
| --- | --- |
| 应禁用服务主体。 | 不要做任何事情。 有意阻止访问。 我们不希望或建议第一方应用程序的资源租户管理员禁用相应的服务主体。 Microsoft服务会自动预配和管理服务主体。 可能是由主租户管理员、应用所有者或 Microsoft 有意在全球范围内禁用了与此服务主体相关联的支持应用程序。 有关详细信息，请参阅 [停用企业应用程序](/zh-cn/entra/identity/enterprise-apps/deactivate-application-portal)。 |
| 服务主体不应被禁用，或者被错误禁用。 | 要求资源租户所有者重新启用服务主体。 重新启用服务主体的一种方法是使用 PowerShell 将参数`-AccountEnabled`设置为 `$true` 。 有关详细信息，请参阅 [Set-AzureADServicePrincipal](/zh-cn/powershell/module/azuread/set-azureadserviceprincipal#example-1-disable-the-account-of-a-service-principal) cmdlet 参考。 |

## 详细信息

有关身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/entra/identity-platform/reference-error-codes)。

若要调查单个错误，请转到 <https://login.microsoftonline.com/error>。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-aadsts7000112-application-is-disabled)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
