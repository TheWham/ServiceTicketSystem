# 错误 AADSTS70001 - 目录中找不到带有标识符的应用程序

## 概要

本文介绍在尝试登录到已与 Microsoft Entra ID 集成的基于 SAML 的单一登录（SSO）配置的应用时收到错误消息“错误AADSTS70001 - 找不到标识符的应用程序”。

## 现象

尝试登录到已设置为使用基于 SAML 的 SSO 进行标识管理Microsoft Entra ID 的应用程序时会收到错误 `AADSTS70001` 。

## 原因

`Issuer`从应用程序发送到 SAML 请求中的 Microsoft Entra ID 的属性与Microsoft Entra ID 中为应用程序配置的标识符值不匹配。

## 解决方法

确保 `Issuer` SAML 请求中的属性与Microsoft Entra ID 中配置的标识符值匹配。

在基于 SAML 的 SSO 配置页上的“基本 SAML 配置”部分，验证**标识符**文本框中的值是否与错误中显示的标识符值匹配。 如果 URL 末尾有尾随斜杠，则还应包含该斜杠。

### 在 Microsoft Entra 管理中心中使用 Test SSO 函数

Microsoft Entra 管理中心可帮助你排查 SAML 配置错误。

![Microsoft Entra 管理中心中测试 SSO 功能的屏幕截图。](media/testing-sso-screen.png)

1. 在Microsoft Entra 管理中心，转到 **企业应用程序** 并单击需要故障排除的应用程序。
2. 使用左侧导航菜单导航到 **“单一登录** ”页
3. 单击 **“测试此应用程序** ”以使用测试 SSO 功能。
4. 将收到的错误复制并粘贴到**“解决错误**”部分，然后单击“获取解决指南”
5. 查看找到的颁发者与标识符之间的差异。
6. 更正颁发者或标识符。

## 更多信息

有关 Active Directory 身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/azure/active-directory/develop/reference-aadsts-error-codes)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-AADSTS70001-app-not-found-in-directory)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
