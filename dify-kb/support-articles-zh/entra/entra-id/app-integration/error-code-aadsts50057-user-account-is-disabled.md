# 错误AADSTS50057 - 用户帐户已禁用

## 概要

本文介绍如何解决用户尝试登录到可与 Microsoft Entra ID 一起使用的应用程序时发生的“AADSTS50057”错误。

## 现象

当用户尝试登录到集成到 Microsoft Entra ID 中的应用程序时，他们会收到“AADSTS50057”错误消息（“用户帐户已禁用”。

## 原因

在资源租户上禁用用户对象。

## 解决方案

让资源租户所有者确定用户帐户被禁用的原因。 然后，执行相应的操作，如下表所示。

| 场景 | 操作 |
| --- | --- |
| 用户帐户应被禁用。 | 不应执行任何操作。 应阻止访问。 |
| 用户帐户不应被禁用，或者被错误禁用。 | 资源租户所有者应重新启用帐户。 重新启用帐户的选项之一是使用 PowerShell 将参数`-AccountEnabled`设置为 `$true` Set-AzureADUser [cmdlet 引用中所述](/zh-cn/powershell/module/azuread/set-azureaduser#parameters)。 |

## 详细信息

有关身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/azure/active-directory/develop/reference-error-codes)。

若要调查单个错误，请转到 <https://login.microsoftonline.com/error>。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-aadsts50057-user-account-is-disabled)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
