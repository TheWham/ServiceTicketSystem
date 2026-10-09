# 排查 Microsoft Entra ID 的 CORS 问题

## 概要

本文提供有关使用 Microsoft Entra ID 时遇到的跨域资源共享（CORS）错误的故障排除和解决的指导。

## 了解 CORS

跨域资源共享（CORS）是一种基于 HTTP 标头的机制，它允许服务器指定其他源（域、方案、端口），以便浏览器可以从这些源加载资源，而不只是从服务器自身的源。 CORS 还依赖于浏览器向托管跨源资源的服务器发出“预检”请求的机制，以检查服务器是否允许实际请求。 在此预检期间，浏览器发送标头，这些标头指示实际请求中使用的 HTTP 方法和标头。

有关 CORS 标头的详细信息，请参阅 [CORS 标头](https://developer.mozilla.org/docs/Glossary/CORS)。

### 重要概念

- 如果资源缺少支持的标头，浏览器会阻止跨域请求。
- 跨域请求通常源自 JavaScript XMLHttpRequest 调用，例如没有用户交互或窗口的直接 HTTP 调用。
- Microsoft Entra ID 在执行交互式登录时未启用 CORS，这意味着 CORS 请求无法直接发送到 Microsoft Entra ID。

## 症状

开发应用程序时，可能会在浏览器控制台日志中遇到以下 CORS 相关错误：

- 示例 1

  > 访问 XMLHttpRequest at 'https://login.microsoftonline.com/tenant\_id/oauth2/v2.0/authorize?client\_id=&redirect\_uri=signin-oidc&response\_type=id\_token&scope=openid%20profile&response\_mode=form\_post&nonce=6370sdfj&state=sdfsdfds-sdfsdfsdf-sd-sdfsdf-T3qwNWW2jRHM&x-client-SKU=ID\_NETSTANDARD2\_0&x-client-ver=5.5.0.0' 从来源“xxx”重定向到来源“yyyy”已被CORS策略阻止：请求的资源上不存在“Access-Control-Allow-Origin”标头。

  URL 以 `https://login.microsoftonline.com/` 开头表明你可能具有 Azure Active Directory B2C 场景。
- 示例 2

  > 访问来自源‘https://contosob2c.b2clogin.com/tfp/tenant\_id/b2c\_1\_v2\_susi\_defaultpage/v2.0/.well-known/openid-configuration’的 URL‘http://localhost:4200’已被 CORS 策略阻止：请求的资源上没有‘Access-Control-Allow-Origin’标头。 如果需要不透明的响应，请将请求的模式设置为“no-cors”，以获取禁用 CORS 的资源。
- 示例 3

  > CORS 策略：对预检请求的响应不会通过访问控制检查：不存在“Access-Control-Allow-Origin”标头。

注释

- 这些错误由 Microsoft Entra ID 生成。 这些错误中的请求 URL 通常以 `https://login.microsoftonline.com` 或 `https://<your-domain>.b2clogin.com` 开头。 后者通常指向 Azure Active Directory B2C 方案。
- 如果错误不是源自 Microsoft Entra ID，则会显示类似“尝试访问位于 `https://app.contoso.com` 的 XMLHttpRequest”。本文不提供解决外部 CORS 问题的指导。 在这种情况下，需要在该环境中配置 CORS。

## 原因

若要识别您的情境和根本原因，请使用 Fiddler 工具捕捉失败请求。 在 Fiddler 捕获中查找`XMLHttpRequest`或 AJAX 请求，你会看到发生 302 重定向到`https://login.microsoftonline.com/`。

### 示例请求和响应

请求：

```
GET https://login.microsoftonline.com.com/domain.onmicrosoft.com/oauth2/v2.0/authorize?... HTTP/1.1
Host: login.microsoftonline.com
Connection: keep-alive
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
Accept-Encoding: gzip, deflate, br
Accept-Language: en-US,en;q=0.9
Origin: https://app.domain.com
```

响应：

```
HTTP/1.1 200 OK
Cache-Control: no-store, no-cache
Pragma: no-cache
Content-Type: text/html; charset=utf-8
Expires: -1
Vary: Accept-Encoding
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-DNS-Prefetch-Control: on
P3P: CP="DSP CUR OTPi IND OTRi ONL FIN"
Set-Cookie:  ...
Referrer-Policy: strict-origin-when-cross-origin
Date: Tue, 24 Nov 2020 19:08:05 GMT
Content-Length: 194559
<!-- Copyright (C) Microsoft Corporation. All rights reserved. -->
<!DOCTYPE html>
<html dir="ltr" class="" lang="en">
<head>
```

可以注意到请求包含标头 `Origin` ，但响应中没有 `Access-Control-Allow-Origin` 标头。 尝试通过 `XMLHttpRequest` 终结点传递访问令牌或身份验证 Cookie 时，安全令牌将失效。 API 将重定向到 Microsoft Entra ID 登录页，而不是返回 401 HTTP 状态代码。 由于此重定向，并且Microsoft Entra ID 不支持 CORS 进行交互式登录，因此 Web 浏览器将引发 CORS 错误。

## 常规解决方案

实现应用程序体系结构以遵循 OAuth2 和 OIDC 标准。 此解决方案可以确保前端应用程序获取访问令牌，并在向 API 发出`Authorization`请求时将其`XMLHttpRequest`包含在请求的标头中。 下面是一些 [单页应用程序示例](/zh-cn/entra/identity-platform/sample-v2-code?tabs=apptype)。

## 基于方案的解决方案

下面是最常见的方案。 本文中未列出每个方案，因为每个环境和应用体系结构都不同。

### 方案 1：使用身份验证 Cookie 的 Web 应用和 Web API

如果 Web 应用或框架 `XMLHttpRequest` 调用其 API 终结点并使用 Web 应用身份验证 Cookie，请检查 `XMLHttpRequest` Fiddler 捕获中的请求。 它可能如下所示：

```
GET https://app.domain.com/… HTTP/1.1

Host: login.microsoftonline.com
Connection: keep-alive
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
Accept-Encoding: gzip, deflate, br
Accept-Language: en-US,en;q=0.9
Origin: https://app.domain.com
Cookie: .AspNet.Cookies=xyz…
```

如果使用 ASP.NET 或 ASP.NET Core，请配置 Microsoft Entra ID，以避免将令牌生存期用作会话生存期。 有关详细信息，请参阅 [自定义中间件身份验证票证以延长用户登录持续时间](customize-authentication-session-expiration)。 可以将 API 身份验证配置为引发错误，而不是执行重定向。 对于 ASP.NET Core，可以使用以下代码：

```
    services.Configure<OpenIdConnectOptions>(OpenIdConnectDefaults.AuthenticationScheme, options =>
{       
    options.Events.OnRedirectToIdentityProvider = (context) =>
    {
    if (!context.Request.Headers["Origin"].IsNullOrEmpty())
    {
        context.Response.StatusCode = (int)HttpStatusCode.Unauthorized;
        context.HandleResponse();
    }
                    
    return Task.FromResult(true);
    };
}
```

然后，实现额外的 `XMLHttpRequest` 逻辑来检查请求是否已完成，并且是重定向或 401 错误。 必须执行操作以告知客户端让用户再次登录。 在大多数情况下，刷新页面允许用户重新进行身份验证。 下面是代码示例：

```
    client.onreadystatechange = () => {
    // API call failed (401) or there was a redirect
    if ((client.readyState === client.DONE && client.responseURL == "") || client.Status == 401) {
    // Handle error such as Refreshing page should allow user to re-authenticate
    window.location.reload(true)
    }
};
```

### 方案 2：使用访问令牌的独立 API

查看 Fiddler 捕获并查看 XMLHttpRequest 请求，它可能如下所示（请注意授权标头）：

```
GET https://app.domain.com/… HTTP/1.1

Host: login.microsoftonline.com
Connection: keep-alive
Authorization: Bearer eyJ0…
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
Accept-Encoding: gzip, deflate, br
Accept-Language: en-US,en;q=0.9
Origin: https://app.domain.com
```

若要解决此问题，请使用以下方法之一：

- [发送有效的令牌](#method-1-send-a-valid-token)
- [使用 JWT 持有者身份验证](#method-2-use-jwt-bearer-authentication)

#### 方法 1：发送有效令牌

如果将访问令牌传递给 API 资源，请确保令牌有效。 检查令牌是否已过期。 如果是，请请求新的访问令牌。 如果使用适用于 JavaScript 的 Microsoft 身份验证库（MSAL.js），请在每次将令牌传递给 API 前使用 `acquireTokenSilent` 来获取一个新令牌。 不要自行缓存此令牌。 始终使用`acquireTokenSilent`直接从 MSAL 获取缓存的令牌。

有关详细信息，请参阅 [单页应用程序：获取令牌以调用 API](/zh-cn/entra/identity-platform/scenario-spa-acquire-token)。

下面是将令牌传递给 API 时的外观示例： [单页应用程序：调用 Web API](/zh-cn/entra/identity-platform/scenario-spa-call-api)。

#### 方法 2：使用 JWT 持有者身份验证

使用 JWT 持有者身份验证，而不是 Open ID Connect。 此实现取决于身份验证中间件，因此请查看其文档，因为每个中间件都有自己的实现策略。 如果令牌无效，JWT 持有者身份验证应向客户端引发 401 错误。 客户端应根据需要处理错误并请求新令牌。 如果使用 Open ID Connect 身份验证方案，API 会尝试将请求重定向到 Microsoft Entra ID 或 B2C，从而导致 CORS 错误。 客户很难处理这种情况。

下面是有关如何设置 JWT Bearer 身份验证的几个示例： [Microsoft用于身份验证和授权的标识平台代码示例](/zh-cn/entra/identity-platform/sample-v2-code#web-api)。

### 方案 3：将 MSAL.js 与 B2C 或第三方 IdP 配合使用

请确保正确配置`authority`、`knownAuthorities`和`protocolMode`。

```
//…
import { ProtocolMode } from '@azure/msal-common';
//…
function MSALInstanceFactory(): IPublicClientApplication {
  return new PublicClientApplication({
    auth: {
      authority: 'https://contoso.b2clogin.com/tfp/655e51e9-be5e-xxxx-xxxx-38aa6558xxxx/b2c_1_susi/v2.0/',
      clientId: '00001111-aaaa-2222-bbbb-3333cccc4444',
      redirectUri: 'http://localhost:4200',
      knownAuthorities: ['contoso.b2clogin.com'],
      protocolMode: ProtocolMode.OIDC
    },
  });
}
```

有关详细信息，请参阅 [MSAL.js 配置选项](https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md)。

### 方案 4：应用位于负载均衡器后面

如果应用程序位于负载均衡器后面，请检查负载均衡器的会话生存期设置，例如 **会话持久性** 或会话相关性。

### 方案 5：令牌接口的 CORS 错误

单页应用程序唯一支持的流是授权代码流，其中包含代码交换（PKCE）的证明密钥和刷新令牌流，同时将重定向地址配置为单页应用程序。

根据 OAuth2 规范和安全最佳实践，请勿使用以下流程：

- 资源所有者密码凭据 （ROPC）
- 机密客户端流，例如客户端凭据或代理流

单页应用程序不支持所有其他流。 Microsoft Entra ID 和 B2C 不会为不支持的流添加 CORS 标头。

### 方案 6：使用 Microsoft Entra 应用程序代理

如果应用使用 Microsoft Entra 应用程序代理，请参阅 [了解 Microsoft Entra 应用程序代理中的复杂应用程序](/zh-cn/entra/identity/app-proxy/application-proxy-configure-complex-application)。

## 参考文献

- [在 ASP.NET Core 中启用跨源请求 (CORS)](/zh-cn/aspnet/core/security/cors)
- [在 ASP.NET Web API 2 中启用跨域请求](/zh-cn/aspnet/web-api/overview/security/enabling-cross-origin-requests-in-web-api)
- [Azure 应用服务 REST API 教程](/zh-cn/azure/app-service/app-service-web-tutorial-rest-api)
- [Azure API 管理 CORS 策略](/zh-cn/azure/api-management/cors-policy)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/troubleshoot-cross-origin-resource-sharing-issues)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
