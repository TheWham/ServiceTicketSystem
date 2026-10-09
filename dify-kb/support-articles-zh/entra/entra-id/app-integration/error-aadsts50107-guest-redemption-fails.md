# 当来宾用户通过 SAML 外部信任兑换邀请时出现错误AADSTS50107

## 概要

本文提供了Microsoft Entra 身份验证错误AADSTS50107的解决方案。 当来宾用户尝试接受来自使用安全断言标记语言（SAML）外部信任的租户的邀请时，会发生此错误。

## 症状

请考虑以下方案：

- 租户与使用 SAML 或 WS-Fed 身份提供者（IdP）的外部组织建立了直接联合信任。
- 外部组织邀请用户以访客身份加入您的租户。
- 来宾用户尝试兑换邀请。

在此方案中，邀请兑换失败，并显示以下错误消息：

> 错误：AADSTS50107：请求的联合领域对象“”https://abc.contoso.com不存在。

## 原因

当 SAML 响应中的颁发者 URL 值与 Microsoft Entra ID 中配置的 URL 值不匹配时，会出现此问题。 SAML 响应中的颁发者 URL 对应于错误消息中提到的 URL。

## 决议

若要解决此问题，请执行以下步骤：

1. 确保外部 IdP 中的颁发者 URL 与 Microsoft Entra ID 中配置的 URL 匹配。
2. 验证或更新Microsoft Entra ID 中的颁发者 URL，使其与 SAML 响应中的 URL 保持一致。

   若要验证Microsoft Entra ID 中的颁发者 URL，请执行以下步骤：

   1. 以管理员身份登录到 Microsoft Entra 管理中心。
   2. 选择“ **管理**>**外部标识**”。
   3. 选择“ **查看所有标识提供者**”。
   4. 在“ **自定义** ”选项卡下，选择所需的 SAML 信任（例如 `Contoso.com`）。
   5. 为所需的 SAML 信任选择 **“编辑配置”**。
   6. 检查在 Microsoft Entra ID 中配置的颁发者 URL 是否与外部 IdP 发送的 SAML 响应中的值匹配 `saml:Issuer` 。

有关详细信息，请参阅 [添加使用 SAML/WS-Fed 的身份提供者的联合](/zh-cn/entra/external-id/direct-federation)。

## 详细信息

有关Microsoft Entra 身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/azure/active-directory/develop/reference-aadsts-error-codes)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-aadsts50107-guest-redemption-fails)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
