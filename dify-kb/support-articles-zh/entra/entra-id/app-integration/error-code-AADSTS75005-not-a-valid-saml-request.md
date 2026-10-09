# 错误AADSTS75005 - 请求不是有效的 Saml2 协议消息

## 概要

本文描述了您在尝试登录已与 Microsoft Entra ID 集成的应用程序时，会收到错误消息“错误AADSTS75005 - 请求不是有效的 Saml2 协议消息”的问题。

## 现象

使用基于 SAML 的单一登录（SSO）尝试登录使用 Microsoft Entra ID 进行身份管理的应用程序时，您会收到错误 `AADSTS75005` 。

## 原因

Microsoft Entra ID 不支持应用程序为单一登录发送的 SAML 请求。 常见问题如下：

- SAML 请求中缺少必填字段。
- SAML 请求编码的方法。

## 解决方法

1. 捕获 SAML 请求。 按照本教程 [操作，了解如何在 Microsoft Entra ID](/zh-cn/azure/active-directory/manage-apps/debug-saml-sso-issues) 中调试基于 SAML 的应用程序单一登录，了解如何捕获 SAML 请求。
2. 请联系应用程序供应商并共享以下信息：
   - SAML 请求
   - [Microsoft Entra 单一登录 SAML 协议要求](/zh-cn/azure/active-directory/develop/single-sign-on-saml-protocol)

应用程序供应商应验证它们是否支持单一登录的 Microsoft Entra SAML 实现。

## 更多信息

有关 Active Directory 身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/azure/active-directory/develop/reference-aadsts-error-codes)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-AADSTS75005-not-a-valid-saml-request)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
