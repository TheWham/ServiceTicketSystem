# Microsoft Entra ID 应用程序中IDX10501签名验证错误

## 概要

如果客户端应用程序从 Microsoft Entra ID 获取访问令牌并将其发送到资源（API）应用程序，则资源应用程序必须验证令牌。 它使用用于对令牌进行签名的证书中的公钥进行验证。 如果应用程序找不到正确的密钥标识符（kid），它可能会生成类似于以下消息的错误消息：

> IDX10501：签名验证失败。 无法匹配“小孩”

若要解决令牌签名验证错误（如“IDX10501”），请确保应用程序配置为从 Microsoft Entra ID 检索正确的公钥。 根据应用程序类型和签名配置使用适当的密钥发现或元数据终结点。

## 对于 OAuth2 资源应用程序

以下步骤演示 OAuth2 应用程序如何验证从 Microsoft Entra ID 颁发的令牌：

1. 使用 API 客户端执行 [授权代码流](/zh-cn/entra/identity-platform/v2-oauth2-auth-code-flow) 并获取令牌。
2. 使用 [jwt.ms](https://jwt.ms) 解码令牌，并记下 `kid`。
3. 根据Microsoft Entra ID 应用程序版本，使用令牌作为持有者令牌来调用以下密钥发现终结点之一。 API 返回三个密钥。 在 `kid` 步骤 2 中获取的密钥应与密钥发现终结点返回的密钥之一匹配。

   对于 v1.0 应用程序，请使用：

   ```
   https://login.microsoftonline.com/common/discovery/keys
   ```

   对于 v2.0 应用程序，请使用：

   ```
   https://login.microsoftonline.com/common/discovery/v2.0/keys
   ```

## SAML资源应用程序的适用情形

对于 SAML，Microsoft Entra ID 使用特定于应用的证书对令牌进行签名。 若要检索正确的公钥，请执行以下步骤：

1. 使用 API 客户端获取 SAML 应用的访问令牌。
2. 使用以下密钥发现终结点，替换 `<tenant>` 和 `<SAML App ID>` 为您的值。

   ```
   https://login.microsoftonline.com/<tenant>/discovery/keys?appid=<SAML App ID>
   ```
3. 如果应用使用使用 [声明映射策略](/zh-cn/entra/identity-platform/saml-claims-customization)的自定义签名密钥，则必须追加包含 `appid` 应用客户端 ID 的查询参数。 此步骤是检索 `jwks_uri` 指向应用的特定签名密钥信息所必需的。 例如：

   ```
   https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration?appid=00001111-aaaa-2222-bbbb-3333cccc4444
   ```

### 中间件配置示例

若要避免签名验证错误，请将中间件配置为使用正确的元数据终结点。

**OpenID Connect 中间件 （OWIN）**

```
app.UseOpenIdConnectAuthentication(
    new OpenIdConnectAuthenticationOptions
    {
        ClientId = clientId,
        Authority = authority,
        RedirectUri = redirectUri,
        MetadataAddress = "https://login.microsoftonline.com/<tenant>/.well-known/openid-configuration?appid=<SAML App ID>",
        PostLogoutRedirectUri = redirectUri,
    });
```

**JWT 持有者身份验证中间件**

```
app.UseJwtBearerAuthentication(new JwtBearerOptions
{
    Audience = "...",
    Authority = "...",
    MetadataAddress = "https://login.microsoftonline.com/<tenant>/.well-known/openid-configuration?appid=<SAML App ID>",
    TokenValidationParameters = new TokenValidationParameters
    {
        // Additional validation parameters
    }
});
```

**Microsoft.Identity.Web （Web 应用）**

```
services.AddMicrosoftIdentityWebAppAuthentication(Configuration)
        .EnableTokenAcquisitionToCallDownstreamApi()
        .AddInMemoryTokenCaches();

services.Configure<MicrosoftIdentityOptions>(options =>
{
    options.MetadataAddress = "https://login.microsoftonline.com/<tenant>/.well-known/openid-configuration?appid=<SAML App ID>";
});
```

**Microsoft.Identity.Web （Web API）**

```
services.AddMicrosoftIdentityWebApiAuthentication(Configuration);

services.Configure<JwtBearerOptions>(JwtBearerDefaults.AuthenticationScheme, options =>
{
    options.MetadataAddress = "https://login.microsoftonline.com/<tenant>/.well-known/openid-configuration?appid=<SAML App ID>";
});
```

## 后续步骤

若要了解有关 Microsoft Entra ID 签名密钥轮替的详细信息，请参阅 [Microsoft 标识平台中的访问令牌](/zh-cn/entra/identity-platform/access-tokens)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/idx10501-token-signature-validation-error)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
