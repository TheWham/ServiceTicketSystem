# ASP.NET MVC 应用中出现“ValidationContext.Nonce 为 null”错误

## 概要

本文提供了使用 OpenID Connect （OIDC） 中间件在 ASP.NET MVC 应用中可能会遇到的常见非验证错误的解决方案。

## 常见错误消息

根据使用的 .NET 开放 Web 接口版本（OWIN），可能会收到以下错误消息之一：

- IDX21323：RequireNonce 默认为“[PII 已隐藏”。 将IdentityModelEventSource.cs中的“ShowPII”标志设置为 true 以显示它。]”。 OpenIdConnectProtocolValidationContext.Nonce 为 null，OpenIdConnectProtocol.ValidatedIdToken.Payload.Nonce 不为 null。 无法验证 nonce。 如果不需要检查 nonce，请将 OpenIdConnectProtocolValidator.RequireNonce 设置为 false。
- IDX10311：RequireNonce 为“true”（默认值），但 validationContext.Nonce 为 null。 无法验证 nonce。 如果不需要检查 nonce，请将 OpenIdConnectProtocolValidator.RequireNonce 设置为 false。

## 了解 nonce Cookie

ASP.NET OIDC 中间件使用 nonce Cookie 来防止 [重播攻击](/zh-cn/dotnet/framework/wcf/feature-details/replay-attacks)。 如果应用在经过身份验证的请求中找不到 nonce Cookie，则会引发异常。 Cookie 是基于域的。 这意味着，如果为特定域设置了 Cookie，则对该域的所有后续请求都将包括 Cookie，直到它们过期或删除。

以下 Fiddler 跟踪描述了如何在工作流中设置和使用这些 Cookie：

- 在 Frame 116 中，浏览器将请求发送到受 Microsoft Entra ID 保护的 OIDC 应用。 收到请求后，应用将检测到它未进行身份验证。 然后，它会将请求重定向到 Microsoft Entra ID （`login.microsoftonline.com`）进行身份验证。 此外，应用在“302”重定向响应中设置 `OpenIdConnect.nonce` Cookie。

  [![Fiddler Trace 中帧 116 的屏幕截图。](media/troubleshoot-validation-context-nonce-null-mvc/fiddler-trace-start-auth.png)](media/troubleshoot-validation-context-nonce-null-mvc/fiddler-trace-start-auth.png#lightbox)
- 成功身份验证（Frame 120-228）后，Microsoft Entra ID 会将请求重定向回 Web 应用（Frame 229），以及经过身份验证的 ID 令牌。 以前为此域设置的 nonce Cookie 也包含在 POST 请求中。 OIDC 中间件在继续加载页面（通过另一个重定向）之前验证经过身份验证的令牌和 nonce Cookie。 此时，nonce Cookie 的用途已完成，应用通过将过期属性设置为过期来使它失效。

  [![与身份验证相关的 Fiddler 跟踪帧的屏幕截图。](media/troubleshoot-validation-context-nonce-null-mvc/fiddler-trace-after-auth.png)](media/troubleshoot-validation-context-nonce-null-mvc/fiddler-trace-after-auth.png#lightbox)

## 解决方案

### 原因 1：多个域用于同一网站

浏览器最初导航到域 A（Frame 9）上的应用，并且为此域设置了 nonce Cookie。 稍后，Microsoft Entra ID 会将经过身份验证的令牌发送到域 B（Frame 91）。 由于重定向到域 B 不包括 nonce Cookie，因此 Web 应用将 `validationContext.Nonce is null` 引发错误。

[![与原因 1 相关的 Fiddler 跟踪帧的屏幕截图。](media/troubleshoot-validation-context-nonce-null-mvc/fiddler-trace-multiple-domains.png)](media/troubleshoot-validation-context-nonce-null-mvc/fiddler-trace-multiple-domains.png#lightbox)

### 解决方案 1

若要解决此问题，请执行以下步骤：

1. 将请求重定向回身份验证后最初使用的域。 若要控制 Azure AD 将经过身份验证的请求发送回应用的位置，请在`OpenIdConnectAuthentications.RedirectUri`方法中设置`ConfigureAuth`该属性。
2. 在应用注册中配置重定向 URI（回复 URL）。 否则，可能会收到以下错误：AADSTS50011：请求中指定的回复 URL 与为应用配置的 Azure 配置的回复 URL 不匹配。 有关详细信息，请参阅 [OpenID 身份验证](error-code-aadsts50011-redirect-uri-mismatch)AADSTS50011错误。

### 原因 2：缺少 SameSite 属性

[由于 SameSite Cookie 安全更新](/zh-cn/azure/active-directory/develop/howto-handle-samesite-cookie-changes-chrome-browser?tabs=dotnet)，身份验证过程中涉及的所有 Cookie（包括 Nonce Cookie）都应包含以下属性：

- SameSite=None
- 安全

有关详细信息，请参阅 [SameSite Cookie 和用于 .NET](/zh-cn/aspnet/samesite/owin-samesite) 的 Open Web 界面。

![缺少 SameSite 属性 Fiddler 跟踪的屏幕截图。](media/troubleshoot-validation-context-nonce-null-mvc/fiddler-trace-misisng-samesite.png)

### 解决方案 2

若要确保包括这两个必需属性，请执行以下步骤：

1. 使用 HTTPS 协议导航到 Web 应用。
2. 更新 .NET Framework 和 NuGet 包：
   - 对于 .NET Framework 应用：将 .NET Framework 升级到版本 4.7.2 及相关的 NuGet 包（Microsoft.Owin.Security.OpenIdConnect，Microsoft.Owin）升级到版本 4.1.0+。
   - 对于 .NET Core 应用：
     - 版本 2。*x* 应用应使用 .NET Core 2.1+。
     - 版本 3。*x* 应用应使用 .NET Core 3.1+。

Startup.Auth.cs的示例配置代码：

```
using System.Configuration;
using Owin;
using Microsoft.Owin.Security;
using Microsoft.Owin.Security.Cookies;
using Microsoft.Owin.Security.OpenIdConnect;
using System.Threading.Tasks;
using Microsoft.Owin.Security.Notifications;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;

namespace NetWebAppOIDC2
{
    public partial class Startup
    {
        private static string clientId = ConfigurationManager.AppSettings["ida:ClientId"];
        private static string aadInstance = ConfigurationManager.AppSettings["ida:AADInstance"];
        private static string tenantId = ConfigurationManager.AppSettings["ida:TenantId"];
        private static string postLogoutRedirectUri = ConfigurationManager.AppSettings["ida:PostLogoutRedirectUri"];
        private static string authority = aadInstance + tenantId;

        public void ConfigureAuth(IAppBuilder app)
        {
            app.SetDefaultSignInAsAuthenticationType(CookieAuthenticationDefaults.AuthenticationType);

            app.UseCookieAuthentication(new CookieAuthenticationOptions());
            app.UseOpenIdConnectAuthentication(
                new OpenIdConnectAuthenticationOptions
                {
                    ClientId = clientId,
                    Authority = authority,
                    PostLogoutRedirectUri = postLogoutRedirectUri,
                    RedirectUri = "https://localhost:44313",
                    
                    Notifications = new OpenIdConnectAuthenticationNotifications
                    {
                        AuthenticationFailed = OnAuthenticationFailed
                    }

                    // Don't use SystemwebCookieManager class here to override the default CookieManager because that seems to negate the SameSite cookie attribute that's being set.
                    // CookieManager = new SystemWebCookieManager()

                });
        }

        private Task OnAuthenticationFailed(AuthenticationFailedNotification<OpenIdConnectMessage, OpenIdConnectAuthenticationOptions> context)
        {
            context.HandleResponse();
            context.Response.Redirect("/?errormessage=" + context.Exception.Message);
            return Task.FromResult(0);
        }
    }
}
```

**第三方信息免责声明**

本文中提到的第三方产品由 Microsoft 以外的其他公司提供。 Microsoft 不对这些产品的性能或可靠性提供任何明示或暗示性担保。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/troubleshoot-validation-context-nonce-null-mvc)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
