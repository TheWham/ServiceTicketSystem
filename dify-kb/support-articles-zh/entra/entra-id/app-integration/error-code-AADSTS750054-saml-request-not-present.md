# 错误 AADSTS750054 - 在发出 SAML 重定向绑定的 HTTP 请求时必须以查询字符串参数的形式提供 SAMLRequest 或 SAMLResponse

## 概要

本文介绍收到错误消息“错误AADSTS750054 - SAMLRequest 或 SAMLResponse 必须作为 SAML 重定向绑定的 HTTP 请求中的查询字符串参数存在。”尝试登录到已与 Microsoft Entra ID 集成的基于 SAML 的单一登录（SSO）配置的应用时。”

## 现象

尝试登录到已设置为使用基于 SAML 的 SSO 进行标识管理Microsoft Entra ID 的应用程序时收到错误 `AADSTS750054` 。

## 原因

Microsoft Entra ID 无法识别 HTTP 请求中的 URL 参数中的 SAML 请求。 如果将 SAML 请求发送到 Microsoft Entra ID 时，应用程序未使用 HTTP 重定向绑定，则可能会发生这种情况。

## 解决方法

应用程序需要使用 HTTP 重定向绑定发送在位置标头中编码的 SAML 请求。 有关如何实现它的详细信息，请阅读 SAML 协议规范文档中的“HTTP 重定向绑定”部分。

大多数情况下，此错误是由于以下问题之一导致的：

1. 确保在应用程序端启用单一登录。
2. 应用程序必须支持服务提供商发起的单一登录（有时称为 SP 发起的 SSO）。 为仅支持标识提供者发起的单一登录的应用程序输入登录 URL 时，可能会导致在未收到 SAML 响应的情况下从应用程序反弹。
3. 验证是否已正确配置登录 URL。

### 在 Microsoft Entra 管理中心中使用 Test SSO 函数

Microsoft Entra 管理中心可帮助你排查 SAML 配置错误。

![Microsoft Entra 管理中心中测试 SSO 功能的屏幕截图。](media/testing-sso-screen.png)

1. 在Microsoft Entra 管理中心，转到 **企业应用程序** 并单击需要故障排除的应用程序。
2. 使用左侧导航菜单导航到 **“单一登录** ”页
3. 单击 **“测试此应用程序** ”以使用测试 SSO 功能。
4. 将收到的错误复制并粘贴到**“解决错误**”部分，然后单击“获取解决指南”
5. 按照步骤排查错误 `AADSTS750054`

## 更多信息

有关 Active Directory 身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/azure/active-directory/develop/reference-aadsts-error-codes)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-AADSTS750054-saml-request-not-present)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
