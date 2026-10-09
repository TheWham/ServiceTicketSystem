# 错误AADSTS50173 - 提供的授权因被吊销而过期

## 概要

本文提供有关尝试登录应用程序时解决错误代码AADSTS50173的指导。

## 症状

当用户尝试登录到使用 Microsoft Entra ID 身份验证的应用程序时，他们会收到以下错误消息：

> `AADSTS50173: The provided grant has expired due to it being revoked, a fresh auth token is needed. The user might have changed or reset their password. The grant was issued on '{authTime}' and the TokensValidFrom date (before which tokens are not valid) for this user is '{validDate}'.`

## 原因

如果吊销用于身份验证的刷新令牌，则会发生此错误。 如果出现以下情况，则会出现此问题：

- 用户更改或重置其密码。
- 刷新令牌过期。
- 管理员撤销刷新令牌。

有关更多信息，请参阅：

- [刷新Microsoft 标识平台中的令牌](/zh-cn/entra/identity-platform/refresh-tokens#token-revocation)
- [在 Microsoft Entra ID 中撤销用户访问权限](/zh-cn/entra/identity/users/users-revoke-access)

## 解决方案

若要解决此问题，请遵循适用的步骤。

### 对于用户

在遇到问题的应用程序中，尝试找到重新进行身份验证或清除任何缓存的令牌信息的选项。 还可以通过注销并重新登录到应用程序来执行这些作（如果此步骤适用或可用）。

### 适用于应用程序开发人员

如果应用程序正在使用 [Microsoft身份验证库（MSAL），](/zh-cn/entra/identity-platform/msal-overview)请按照 [本指南处理 MSAL](/zh-cn/entra/msal/dotnet/advanced/exceptions/msal-error-handling) 中的错误和异常。

如果应用程序未使用 MSAL，请按照本指南 [处理 MSAL](/zh-cn/entra/msal/dotnet/advanced/exceptions/msal-error-handling) 中的错误和异常，并尝试在应用程序上实现类似的方法。 目标是请求用户重新进行身份验证并获取新的令牌。

## 详细信息

有关身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/entra/identity-platform/reference-error-codes)。

若要调查单个错误，请转到 <https://login.microsoftonline.com/error>。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-aadsts50173-grant-expired-revoked)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
