# SAML 身份验证AADSTS50011错误 - 请求中指定的回复 URL 不匹配

## 概要

本文提供了AADSTS50011错误的解决方案，该错误是在联合身份验证期间与 Microsoft Entra ID 一起发生的。

## 现象

尝试登录到已设置为使用基于 SAML 的 SSO 进行标识管理Microsoft Entra ID 的应用程序时会收到错误 `AADSTS50011` 。

> 错误AADSTS50011 - 回复 URL 与为应用程序 <GUID> 配置的回复 URL 不匹配。 请确保在请求中发送的答复 URL 与添加到Azure 门户中的应用程序的答复 URL 匹配。
> <https://aka.ms/urlMismatchError>导航到详细了解如何解决此问题。“尝试登录到已与 Microsoft Entra ID 集成的基于 SAML 的单一登录（SSO）配置的应用时。

## 原因

`AssertionConsumerServiceURL` SAML 请求中的值与Microsoft Entra ID 中配置的回复 URL 值或模式不匹配。 SAML 请求中的 `AssertionConsumerServiceURL` 值是错误中显示的 URL。

## 解决方法

要解决该问题，请执行以下步骤：

1. 确保 `AssertionConsumerServiceURL` SAML 请求中的值与Microsoft Entra ID 中配置的回复 URL 值匹配。
2. 验证或更新“回复 URL”文本框中的值，以匹配 SAML 请求中的 `AssertionConsumerServiceURL` 值。

例如，请参阅以下文章，了解有关如何在 Microsoft Entra ID 中配置值的详细步骤：

- [教程：Microsoft Entra SSO 与Salesforce 的集成](/zh-cn/azure/active-directory/saas-apps/salesforce-tutorial)

注意

回复 URL 也称为重定向 URI。 这些值取决于正在使用的应用程序。 应从应用程序供应商处获取这些值。

更新 Microsoft Entra ID 中的回复 URL 值后，它与 SAML 请求中应用程序发送的值匹配后，应该能够登录到应用程序。

## 更多信息

有关 Active Directory 身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/azure/active-directory/develop/reference-aadsts-error-codes)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-AADSTS50011-reply-url-mismatch)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
