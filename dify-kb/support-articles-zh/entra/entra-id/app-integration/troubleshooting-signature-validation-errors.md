# 排查访问令牌签名验证错误

## 概要

当资源提供程序验证访问令牌的签名时，会发生签名验证错误。 这些错误可能会导致签名密钥不可用或无法验证签名。 本文可帮助你排查此类错误，并在某些方案中提供解决方案。

## 步骤 1：解码访问令牌

1. 获取将发送到资源提供方的访问令牌。
2. 解码访问令牌并查看以下声明：

   - `aud` （受众）
   - `iss` （颁发者）
   - `kid` （密钥 ID）

   注释

   可以使用<https://jwt.ms>解码访问令牌。

## 步骤 2：验证访问令牌的受众声明

如果将 Microsoft Graph 访问令牌发送到非Microsoft Graph 资源提供程序，则会收到签名验证错误。 只有 Microsoft Graph 才能验证此类令牌。 Microsoft Graph 令牌的 `aud` 声明值是以下之一：

- `https://graph.microsoft.us`
- `https://graph.microsoft.us/`
- `https://graph.microsoft.com`
- `https://graph.microsoft.com/`
- `https://dod-graph.microsoft.us`
- `https://dod-graph.microsoft.us/`
- `00000003-0000-0000-c000-000000000000`

若要解决签名验证错误，请确保已为资源提供方获取正确的访问令牌，并且确保资源提供方预期其 `aud` 声明。

访问令牌的受众声明由在请求中发送的 `scope` 参数在获取访问令牌时确定。 例如，为了获取`https://api.contoso.com`的访问令牌，请使用类似`https://api.contoso.com/read`的范围。

有关详细信息，请参阅[配置应用程序以公开 Web API](/zh-cn/entra/identity-platform/quickstart-configure-app-expose-web-apis)。

## 步骤 3：验证签名密钥

对于其他场景，资源提供程序根据 OpenId Connect 元数据配置确定从何处获取签名密钥，并根据访问令牌的`kid`声明来选择使用哪个签名密钥。 可以在资源提供程序（例如自定义 API 或 API 身份验证层）上配置 OpenId Connect 元数据。

如果您使用 Microsoft 身份验证库（如 Microsoft 身份验证库（MSAL）或 Microsoft Identity Web）为应用程序进行身份验证，那么指向 OpenId Connect 元数据配置的默认值是 `MetadataAddress`。

如果已配置租户 ID， `MetadataAddress` 则为 `https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration`。 如果您已配置`Authority`如`https://login.microsoftonline.us/{tenant-id}`，那么`MetadataAddress`将为`https://login.microsoftonline.us/{tenant-id}/v2.0/.well-known/openid-configuration`。

OpenId Connect 元数据终结点包括 `jwks_uri` 属性（也称为发现密钥终结点），该终结点指定签名密钥的位置。 根据所使用的 OpenId Connect 元数据终结点，它为属性 `jwks_uri` 返回不同的 URL。 下面是一个提供几个示例的表：

| 元数据端点 | 发现密钥端点 |
| --- | --- |
| `https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration` | `https://login.microsoftonline.com/common/discovery/v2.0/keys` |
| `https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration` | `https://login.microsoftonline.com/{tenant-id}/discovery/v2.0/keys` |
| `https://contosob2c.b2clogin.com/{tenant-id}/{policy}/v2.0/.well-known/openid-configuration` | `https://contosob2c.b2clogin.com/{tenant-id}/{policy}/discovery/v2.0/keys` |

发现密钥终结点包括多个签名密钥。 如果手动使用特定密钥，而不是访问令牌或缓存密钥中提供的签名密钥，则由于常规密钥轮换，签名验证可能不会成功。 有关详细信息，请参阅 [Microsoft 标识平台中的签名密钥自动更换](/zh-cn/entra/identity-platform/signing-key-rollover)。

发现密钥终结点的内容如下所示：

```
"keys": [
		{
			"kty": "RSA",
			"use": "sig",
			"kid": "<kid-value>",
			"x5t": "<x5t-value>",
			"n": "<n-value>",
			"e": "<e-value>",
			"x5c": [
				"<x5c-value>"
			],
			"issuer": "https://login.microsoftonline.com/{tenant-id}/v2.0"
		},
```

`kid`访问令牌的声明必须与根据`kid`属性可在发现密钥终结点上使用的其中一个密钥匹配。 如果不匹配，有两个可能的原因：

- Microsoft Entra ID 和 Azure Active Directory （AD） B2C 使用不同的签名密钥。
- 该应用程序已启用安全断言标记语言（SAML）单点登录（SSO）。

若要解决此不匹配问题，请转到 [步骤 4：验证访问令牌的 iss 声明](#step-4-validate-the-iss-claim-of-the-access-token)。

## 步骤 4：验证访问令牌的 iss 声明

### 方案 1：Microsoft Entra ID 和 Azure AD B2C 使用不同的签名密钥

检查访问令牌的`iss`声明。 声明 `iss` 指示令牌的发行方。

- 对于 Microsoft Entra ID 颁发的令牌， `iss` 声明具有以下格式之一：

  - `https://sts.windows.net/{tenant-id}` （用于 v1.0 版本的令牌）
  - `https://login.microsoftonline.com/{tenant-id}/v2.0` （用于 v2.0 token）
- 对于 Microsoft Entra 外部 ID 颁发的令牌，`iss` 声明格式如下：

  `https://{your-domain}.ciamlogin.com/{tenant-id}/v2.0/`
- 对于 Azure AD B2C 颁发的令牌， `iss` 声明采用以下格式：

  `https://{your-domain}.b2clogin.com/tfp/{tenant-id}/{policy-id}/v2.0/`

若要避免签名验证错误，请根据令牌颁发者正确配置 OpenID Connect 元数据：

- 对于Microsoft Entra ID 颁发的令牌，请确保 OpenId Connect 元数据配置如下所示 `https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration`。

  有关详细信息，请参阅 [Microsoft 标识平台上的 OpenID Connect](/zh-cn/entra/identity-platform/v2-protocols-oidc)。
- 对于 Microsoft Entra 外部 ID 颁发的令牌，请确保 OpenID Connect 元数据配置如下所示：`https://{tenant-domain}.ciamlogin.com/{tenant-id}/v2.0/.well-known/openid-configuration`。

  有关详细信息，请参阅 [设置 OpenID Connect 标识提供者](/zh-cn/entra/external-id/customers/how-to-custom-oidc-federation-customers#set-up-your-openid-connect-identity-provider)。
- 对于 Azure AD B2C 颁发的令牌，请确保 OpenId Connect 元数据配置如下所示 `<https://{your-domain}.b2clogin.com/{tenant-id}/{b2c-policy}/v2.0/.well-known/openid-configuration`。

  有关详细信息，请参阅 [Azure Active Directory B2C 中使用 OpenID Connect 进行 Web 登录](/zh-cn/azure/active-directory-b2c/openid-connect)。

### 方案 2：为 SAML SSO 启用应用程序

假设访问令牌是从 Microsoft Entra ID 而不是 Azure AD B2C 颁发的。 为 SAML SSO 启用 Microsoft Entra ID 中的应用程序时，用于对令牌进行签名的签名密钥是 SAML 签名证书。 因此，在默认发现密钥终结点上查找 `kid` 访问令牌中的声明时，通常 `https://login.microsoftonline.com/common/discovery/v2.0/keys`可能不会列出该声明。

不建议对同一应用程序同时使用 OAuth2 和 SAML。 若要解决此问题，请使用以下方法之一将应用程序与 OAuth2 和 SAML 分开：

- 为 OAuth2 创建新的应用注册（建议的方法）。
- 将企业应用程序转换为仅使用 OAuth2。

  为此，请通过在`preferredSingleSignOnMode`上将`servicePrincipal`属性设置为`null`或`oidc`来禁用 SAML SSO。
- 更新资源提供程序的 OpenId Connect 元数据配置以包括 `?appid={application-id}`，例如 `https://login.microsoftonline.us/<tenant-id>/v2.0/.well-known/openid-configuration?appid=<application-id>`。

  注释

  此解决方案难以实施，并且根据资源提供商的情况，可能无法实现。

## OpenId Connect 元数据配置示例

请确保根据访问令牌是从 Microsoft Entra ID 颁发、从 Azure AD B2C 颁发，还是通过添加 `?appid={application-id}` 来设置 OpenId Connect 元数据配置。

通常，正确配置 Microsoft Entra ID`Instance`及`Tenant`或`Authority`可以解决签名验证错误。

- `Instance`

  Microsoft Entra ID 实例为 `https://login.microsoftonline.com`。 有关Microsoft Entra ID 实例的详细信息，请参阅 [国家/地区云](/zh-cn/entra/identity-platform/authentication-national-cloud)。
- `Tenant`

  租户将是 `contoso.onmicrosoft.com`。 还可以使用目录标识符或任何已验证的域。 我们建议使用目录 ID 或 Microsoft Entra ID 提供的初始域（例如 `contoso.onmicrosoft.com`）。
- `Authority`

  如果配置了`Authority`，则不需要`Instance`和`Tenant`，因为`Authority`符合以下格式：

  `{Instance}/{Tenant}`

  所以，`Authority` 就像 `https://login.microsoftonline.com/contoso.onmicrosoft.com`。

通常，`MetadataAddress`是基于`Instance`/`Tenant`/`Authority`配置构建的，并在末尾自动连接`/.well-known/openid-configuration`。 以下几个部分展示了如何手动指定 `MetadataAddress`。

### 示例 1：使用 Microsoft Identity Web

```
services.AddAuthentication(OpenIdConnectDefaults.AuthenticationScheme)
                    .AddMicrosoftIdentityWebApp(
                       options =>
                       {
                           Configuration.Bind("AzureAd", options);
                           options.MetadataAddress = metadataAddress,
                           
                       })
                       .EnableTokenAcquisitionToCallDownstreamApi(options => Configuration.Bind("AzureAd", options), initialScopes)
                         .AddMicrosoftGraph(Configuration.GetSection("GraphAPI"))
                         .AddInMemoryTokenCaches();
```

有关详细信息，请参阅 [Microsoft 身份验证 Web 自定义](https://github.com/AzureAD/microsoft-identity-web/wiki/customization)。

### 示例 2：使用 ASP.NET 标准框架

- `UseWindowsAzureActiveDirectoryBearerAuthentication`

  将元数据设置为 `https://login.microsoftonline.com/{tenant-id}/.well-known/openid-configuration`.

  ```
  app.UseWindowsAzureActiveDirectoryBearerAuthentication(
              new WindowsAzureActiveDirectoryBearerAuthenticationOptions
              {
                  MetadataAddress = metadataAddress,
                  Tenant = ConfigurationManager.AppSettings["ida:Tenant"],
  ```
- `UseOpenIdConnectAuthentication`

  您可以将 `Authority` 设置为 `https://login.microsoftonline.com/{tenant-id}/v2.0` 中的任意一项：

  ```
  public void Configuration(IAppBuilder app)
      {
          app.SetDefaultSignInAsAuthenticationType(CookieAuthenticationDefaults.AuthenticationType);

          app.UseCookieAuthentication(new CookieAuthenticationOptions());
          app.UseOpenIdConnectAuthentication(
          new OpenIdConnectAuthenticationOptions
          {
              // Sets the ClientId, authority, RedirectUri as obtained from web.config
              ClientId = clientId,
              Authority = authority,
  ```

  或将`MetadataAddress`设置至`https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration`：

  ```
   public void Configuration(IAppBuilder app)
      {
          app.SetDefaultSignInAsAuthenticationType(CookieAuthenticationDefaults.AuthenticationType);

          app.UseCookieAuthentication(new CookieAuthenticationOptions());
          app.UseOpenIdConnectAuthentication(
          new OpenIdConnectAuthenticationOptions
          {
              // Sets the ClientId, authority, RedirectUri as obtained from web.config
              ClientId = clientId,
              MetadataAddress = metadataAddress,
  ```

### 示例 3：使用 Azure 应用服务身份验证

请参阅 [配置应用服务或 Azure Functions 应用以使用 Microsoft Entra 登录](/zh-cn/azure/app-service/configure-authentication-provider-aad)。

### 示例 4：使用 Azure API 管理

请参阅 [使用 Azure AD B2C 保护 Azure API 管理 API](/zh-cn/azure/active-directory-b2c/secure-api-management?tabs=app-reg-ga)。

## 参考文献

[验证令牌](/zh-cn/entra/identity-platform/access-tokens#validate-tokens)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/troubleshooting-signature-validation-errors)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
