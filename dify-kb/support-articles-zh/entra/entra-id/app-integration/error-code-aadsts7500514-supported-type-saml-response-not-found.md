# AADSTS7500514 - 在 PingFederate 中找不到受支持的 SAML 响应类型

## 概要

本文可帮助你排查 PingFederate 联合帐户尝试使用 Microsoft Entra ID（以前称为 Azure Active Directory）进行身份验证时返回的错误代码 `AADSTS7500514` 。

## 症状

当联合帐户尝试使用基于 Microsoft 身份验证库 （MSAL） 或基于 Active Directory 身份验证库 （ADAL） 的应用程序中的 Microsoft Entra ID 进行身份验证时，登录将失败。 将显示以下错误消息：

```
{
     error: "invalid_request",
     error_description: "AADSTS7500514: A supported type of SAML response was not found. The supported response types are 'Response' (in XML namespace 'urn:oasis:names:tc:SAML:2.0:protocol') or 'Assertion' (in XML namespace 'urn:oasis:names:tc:SAML:2.0:assertion').
     ....
     error_uri: "https://login.microsoftonline.com/error?code=7500514"
}
```

该错误通常发生在以下环境中：

- 使用 [PingFederate](https://www.pingidentity.com/) 作为身份提供商的联合账户。
- 身份提供商已配置为使用 WS-Trust 协议颁发 SAML 1.1 令牌。
- 应用程序使用以下 API 之一进行身份验证：
  - MSAL `AcquireTokenByUserNamePassword` 方法。
  - ADAL `AcquireToken`（string resource，string clientId，UserCredential userCredential）方法。
  - 使用这些 MSAL 或 ADAL 方法的任何 PowerShell 模块。

## 原因

由于 [ADAL 现已弃用](/zh-cn/entra/identity/monitoring-health/recommendation-migrate-from-adal-to-msal)，因此本文重点介绍 MSAL。

如果来自 PingFederate 的 SAML 响应不包含 SAML 版本或使用 MSAL 无法识别的格式，则会出现此问题。 通常，这种情况是由 Microsoft Entra ID 的 PingFederate 端配置错误引起的。

### 根本原因分析：SAML 令牌版本识别

当 MASL 对联合帐户进行身份验证时，它会确定该帐户是托管帐户还是联合帐户。

对于托管帐户，MSAL 使用 [资源所有者密码凭据授权流程](/zh-cn/entra/identity-platform/v2-oauth-ropc)。 对于联合账户，它使用 [SAML 断言授权流程](/zh-cn/azure/active-directory/develop/v2-saml-bearer-assertion)。

SAML Assertion Grant 流程包含两个步骤：

- 客户端应用程序向联合身份提供商进行身份验证以获取 SAML 令牌。
- 客户端使用获取的 SAML 令牌从 Microsoft Entra ID 获取 OAuth 2.0 JWT 令牌。

身份验证错误通常发生在步骤 1 中，在该步骤中，客户端应用程序必须解析来自身份提供商的 SAML 响应，以确定 SAML 令牌的版本。 MSAL 在标识提供者的 SAML 响应中查找以下属性：

- `saml:Assertion`
- `TokenType`

以下是来自终端节点的 `/UserNameMixed` AD FS SAML 响应示例：

- `saml:Assertion`：主要版本 = 1，次要版本 = 1
- `TokenType`: `urn:oasis:names:tc:SAML:1.0:assertion`

[![ADFS SAML 响应的屏幕截图。](media/error-code-aadsts7500514-supported-type-saml-response-not-found/adfs-saml-response.png)](media/error-code-aadsts7500514-supported-type-saml-response-not-found/adfs-saml-response.png#lightbox)

PingFederate SAML 响应示例（SAML 断言授权流程步骤 1）：

[![PingFederate SAML 响应的屏幕截图，显示用于 SAML 断言授权流程的第 1 步。](media/error-code-aadsts7500514-supported-type-saml-response-not-found/pingid-saml-response.png)](media/error-code-aadsts7500514-supported-type-saml-response-not-found/pingid-saml-response.png#lightbox)

当您比较这些响应时，您会发现 PingFederate 为同一 SAML 1.1 令牌返回不同的 TokenType 值 （`http://docs.oasis-open.org/wss/oasis-wss-saml-token-profile-1.1#SAMLV1.1`）。 但是，MSAL 不支持除 `urn:oasis:names:tc:SAML:1.0:assertion` 之外的任何 TokenType 值。

如果标识提供者在 SAML 响应中返回不同或意外的值，MSAL 可能会错误地将令牌解释为 SAML 2.0。 在这种情况下，它会在 SAML Assertion Grant 流的步骤 2 中使用相应的 `grant_type` 值。

使用 PingFederate 从 MSAL 应用程序发送的请求示例（SAML 断言授权流步骤 2）：

[![使用 PingFederate 在 SAML 断言授予流步骤 2 中从 MSAL 应用程序发送请求的屏幕截图。](media/error-code-aadsts7500514-supported-type-saml-response-not-found/pingid-saml-response-2.png)](media/error-code-aadsts7500514-supported-type-saml-response-not-found/pingid-saml-response-2.png#lightbox)

使用 AD FS 从 MSAL 应用程序发送的请求示例：

[![在 SAML 断言授予流步骤 2 中使用 AD FS 从 MSAL 应用程序发送的请求的屏幕截图。](media/error-code-aadsts7500514-supported-type-saml-response-not-found/pingid-saml-response-3.png)](media/error-code-aadsts7500514-supported-type-saml-response-not-found/pingid-saml-response-3.png#lightbox)

在此步骤中，参数的值 `grant_type` 必须与 SAML 令牌的实际版本一致。 MSAL 应用程序使用以下值之一：

- urn：ietf：params：oauth：grant-type：saml2-bearer - 用于 SAML 2.0 令牌
- urn：ietf：params：oauth：grant-type：saml1\_1-bearer - 用于 SAML 1.1 令牌

在 PingFederate 示例中，MSAL 根据其对 SAML 版本的误解使用 `saml2-bearer` 作为 `grant_type`。 这会导致参数与断言中包含的 SAML 令牌之间的 `grant_type` 版本不匹配，从而导致身份验证错误。

## 解决方案

要解决此问题，请确保将 PingFederate 配置为符合 Microsoft Entra ID 要求。 有关分步说明，请查看以下文章：

- [创建与 Microsoft Entra ID 的连接](https://docs.pingidentity.com/integrations/azure/azure_ad_and_office_365_integration_guide/pf_azuread_office365_integration_creating_a_connection_to_azure_active_directory.html)。

  在 Microsoft Entra ID 连接设置期间，请特别注意以下步骤中的设置：

  1. 配置连接协议。
  2. 在 **Connection Template （连接模板** ） 选项卡上，选择 **Do not use a template for this connection（不对此连接使用模板**），然后选择 **Next（下一步**）。
  3. 在 **Connection Type** 选项卡上，选择 **Browser SSO Profiles**。
  4. 在 Protocol（协议）列表中，选择 **WS-Federation（WS 联合身份验证）**。
  5. 在 **WS-Federation Token Type** 列表中，选择 **SAML 1.1**。
  6. 如果要支持主动联合，请选中 **WS-Trust STS** 复选框。
- [配置 WS-Trust STS](https://docs.pingidentity.com/integrations/azure/azure_ad_and_office_365_integration_guide/pf_azuread_office365_integration_configuring_ws_trust_sts.html)

  配置 WS-Trust STS 时，请确保选择 **SAML 1.1 for Office 365** 作为默认令牌类型。

**第三方信息免责声明**

本文讨论的第三方产品由独立于微软的公司制造。 Microsoft对这些产品的性能或可靠性不作任何明示或暗示的保证。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-aadsts7500514-supported-type-saml-response-not-found)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
