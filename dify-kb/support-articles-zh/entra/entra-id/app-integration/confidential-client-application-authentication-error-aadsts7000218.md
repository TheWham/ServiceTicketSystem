# 机密客户端应用程序向 Microsoft Entra ID 进行身份验证时出错AADSTS7000218

## 概要

本文提供了AADSTS7000218错误的解决方案，该错误在机密客户端应用程序向 Microsoft Entra ID 进行身份验证时发生。

## 症状

当机密客户端应用程序向 Microsoft Entra ID 进行身份验证以获取访问令牌时，将显示以下错误消息：

```
{
    "error": "invalid_client",
    "error_description": "AADSTS7000218: The request body must contain the following parameter: 'client_assertion' or 'client_secret'.\r\nTrace ID: xxx\r\nCorrelation ID: xxx\r\nTimestamp: 2019-08-18 20:38:28Z",
    "error_codes": [7000218],
    ...
}
```

## 原因

出现此问题的原因是应用程序不提供令牌终结点所需的凭据（客户端密码或断言）。 机密客户端在向 Microsoft Entra ID 进行身份验证时必须提供其凭据。

## 决议

若要解决此问题，请在令牌请求中包含客户端机密或断言。

在某些身份验证流方案中，例如 [OAuth 2 资源所有者密码凭据（ROPC）](/zh-cn/entra/identity-platform/v2-oauth-ropc) 授权流或 [OAuth 2 设备授权流](/zh-cn/entra/identity-platform/v2-oauth2-device-code)，在不要求客户端应用程序保密的情况下，允许在 **应用注册**中使用公共客户端流：

1. 在 [Azure 门户中](https://portal.azure.com/)的 **“应用注册**”中，选择应用程序，然后选择“ **身份验证**”。
2. 选择“ **高级设置**>**允许公共客户端流**”。
3. 对于 **“启用以下移动和桌面流**”，请选择“ **是**”。

   [![显示“启用以下移动和桌面流”选项的屏幕截图。](media/confidential-client-application-authentication-error-aadsts7000218/allow-public-client-flows.png)](media/confidential-client-application-authentication-error-aadsts7000218/allow-public-client-flows.png#lightbox)

将默认客户端类型从机密更改为公共会导致安全影响。 有关详细信息，请参阅 [公共客户端和机密客户端应用程序](/zh-cn/entra/identity-platform/msal-client-applications)。

## 了解 Microsoft Entra ID 中的客户端类型

根据 [OAuth 2.0 规范](https://tools.ietf.org/html/rfc6749)中的定义，客户端应用程序分为两种类型：

- 机密客户端：可以安全地存储用于对 Microsoft Entra ID 进行身份验证的机密的客户端。

  例如，客户端是一个 Web 应用程序，其代码和机密存储在未公开给公众的服务器上。 只有管理员才能访问应用程序的机密信息。
- 公共客户端：无法存储任何机密的客户端。

  例如，公共客户端是在不安全或非托管环境中运行的移动或桌面应用程序。

在 Microsoft Entra 应用注册模型中，注册的应用程序既可以是公共客户端，也可以是机密客户端，具体取决于应用程序的使用上下文。 这是因为应用程序可能具有用作公共客户端的部件，而其他部分则设计为用作机密客户端。 根据工作流，应用程序开发人员必须决定应用程序是否应充当公共或机密客户端。 某些 OAuth2 授予流（例如客户端凭据流、授权代码流或 on-Behalf-Of 流）中预期有机密客户端。 它使用流来请求令牌。

## Microsoft Entra ID 如何确定客户端类型

- 方法 1：使用重定向 URI 的类型（应答 URL）

  Microsoft Entra ID 会检查请求中提供的重定向 URI（回复 URL），并使用在应用注册中注册的重定向 URI 进行交叉检查。

  - **Web** 类型的重定向 URI 将应用程序分类为机密客户端。

    [![显示 Web 类型的重定向 URI 的屏幕截图。](media/confidential-client-application-authentication-error-aadsts7000218/web-client-type.png)](media/confidential-client-application-authentication-error-aadsts7000218/web-client-type.png#lightbox)
  - **移动和桌面应用程序的**重定向 URI 将应用程序分类为公共客户端。

    [![显示公共类型的重定向 URI 的屏幕截图。](media/confidential-client-application-authentication-error-aadsts7000218/public-client-type.png)](media/confidential-client-application-authentication-error-aadsts7000218/public-client-type.png#lightbox)
- 方法 2：使用 **“启用以下移动和桌面流** ”选项（未提供回复 URL 时）

  在某些 OAuth 2.0 流中，例如 [OAuth 2 资源所有者密码凭据（ROPC）](/zh-cn/azure/active-directory/develop/v2-oauth-ropc) 授予流、[OAuth 2 设备授权授予](/zh-cn/entra/identity-platform/v2-oauth2-device-code)和集成 Windows 身份验证，令牌请求中不提供回复 URL。 在这些情况下，Microsoft Entra ID 使用应用注册的 **“启用以下移动和桌面流** ”来确定客户端是机密还是公共的。

  - 如果 **“启用以下移动流”和“桌面流** ”设置为 **“是**”，则客户端是公共的。
  - 如果设置为 **“否**”，则客户端是机密的。

### 如何识别应用程序使用的授予类型和重定向 URI

查看应用程序代码或捕获 [Fiddler](https://blogs.aaddevsup.xyz/2018/09/capture-https-traffic-with-http-fiddler/) 跟踪，以检查在 POST 请求中发送到 Microsoft Entra ID 令牌终结点的 `grant_type` 和 `redirect_uri` 参数：

- V1 端点： `https://login.microsoftonline.com/<tenant name>/oauth2/token`
- V2 端点： `https://login.microsoftonline.com/<tenant name>/oauth2/v2.0/token`

下面是 Fiddler 跟踪的示例：

![显示 Fiddler 中的 POST 请求的屏幕截图。](media/confidential-client-application-authentication-error-aadsts7000218/post-request.png)

![显示授予类型的屏幕截图。](media/confidential-client-application-authentication-error-aadsts7000218/grant-type.png)

常见的 OAuth 2.0 流及其关联的 `grant_type` 值如下所示：

| OAuth 2.0 流 | grant\_type 的值 |
| --- | --- |
| [ROPC](/zh-cn/entra/identity-platform/v2-oauth-ropc) | `password` |
| [设备代码](/zh-cn/entra/identity-platform/v2-oauth2-device-code) | `urn:ietf:params:oauth:grant-type:device_code` |
| [授权代码](/zh-cn/entra/identity-platform/v2-oauth2-auth-code-flow) | `authorization_code` |
| [客户端凭据](/zh-cn/entra/identity-platform/v2-oauth2-client-creds-grant-flow) | `client_credentials` |
| [代替](/zh-cn/entra/identity-platform/v2-oauth2-on-behalf-of-flow) | `urn:ietf:params:oauth:grant-type:jwt-bearer` |
| [SAML 持有者声明](/zh-cn/entra/identity-platform/v2-saml-bearer-assertion) | `urn:ietf:params:oauth:grant-type:saml1_1-bearer` |

## 参考文献

[Microsoft身份验证库 （MSAL） 客户端应用程序](https://github.com/AzureAD/microsoft-authentication-library-for-dotnet/wiki/Client-Applications)

**第三方信息免责声明**

本文讨论的第三方产品由独立于微软的公司制造。 Microsoft对这些产品的性能或可靠性不作任何明示或暗示的保证。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/confidential-client-application-authentication-error-aadsts7000218)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
