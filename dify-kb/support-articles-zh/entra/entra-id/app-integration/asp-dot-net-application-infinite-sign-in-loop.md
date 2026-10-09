# ASP.NET 应用程序和 Microsoft Entra ID 之间的无限登录循环

## 概要

本文提供了 ASP.NET 应用程序在使用 Microsoft Entra ID 登录期间遇到无限重定向循环的问题的解决方案。

## 症状

运行早期版本的适用于 .NET 的 Open Web Interface （OWIN） 中间件的 ASP.NET 应用程序无法识别来自 Microsoft Entra ID 的经过身份验证的请求。 它不断将请求发送回 Microsoft Entra ID 进行登录，从而导致无限循环问题。 以下错误消息可能在浏览器中显示：

> 我们无法让您登录。 请重试。

## 原因

此问题是由于 OWIN 早期版本中的 cookie 管理不当问题（[已知的 Katana 错误](https://github.com/aspnet/AspNetKatana/wiki/System.Web-response-cookie-integration-issues)）。

### 如何识别 Katana 漏洞

捕获 Fiddler 跟踪并检查后面的一个重定向帧回到 Web 应用程序。 请注意，在以下屏幕截图中，帧 58 中的请求包含多个 OpenIdConnect.nonce Cookie（红色圆圈）。 在工作方案中，在身份验证之前，应只设置一个 OpenIdConnect.nonce Cookie。 成功对请求进行身份验证后，将销毁此 nonce Cookie，ASP.NET 设置其自己的会话 Cookie。 由于此 bug，你会看到这些 nonce Cookie 的积聚。

[![显示多个 OpenIdConnect nonce Cookie 的屏幕截图。](media/asp-dot-net-application-infinite-sign-in-loop/openidconnet-nonce-cookies.png)](media/asp-dot-net-application-infinite-sign-in-loop/openidconnet-nonce-cookies.png#lightbox)

## 解决方案 1：升级到 ASP.NET Core

此问题已在 ASP.NET Core 和更高版本的 Katana OWIN 中解决，适用于 ASP.NET。 若要解决此问题，请升级应用程序以使用 ASP.NET Core。

如果必须继续使用 ASP.NET，请执行以下步骤：

- 将应用程序的 Microsoft.Owin.Host.SystemWeb 包更新到 3.1.0.0 或更高版本。
- 修改代码以使用新 Cookie 管理器类之一，例如：

  ```
  app.UseCookieAuthentication(new CookieAuthenticationOptions 
  { 
      AuthenticationType = "Cookies", 
      CookieManager = new Microsoft.Owin.Host.SystemWeb.SystemWebChunkingCookieManager() 
  });
  ```

  或

  ```
  app.UseCookieAuthentication(new CookieAuthenticationOptions() 
  { 
      CookieManager = new SystemWebCookieManager() 
  });
  ```

## 解决方案 2：更正重定向 URL

在某些情况下，应用程序托管在虚拟目录或应用程序下，而不是网站的根目录下， [解决方案 1](#solution-1-upgrade-to-aspnet-core) 可能不起作用。 有关详细信息，请参阅 [指定重定向后 AAD 身份验证的无限重定向循环](https://stackoverflow.com/questions/44397715/infinite-re-direct-loop-after-aad-authentication-when-redirect-is-specified) 和 [当重定向 URL 不在网站根路径下时 Microsoft 帐户 OAuth2 登录失败](https://github.com/aspnet/AspNetKatana/issues/203)。

例如，假设你有以下环境：

- 网站的根： `https://mysite` – 此站点在 *应用程序池 1* 下运行。
- 根目录下的应用程序 *test2* ： `https://mysite/test2` – 此应用程序在 *应用程序池 2* 下运行。
- ASP.NET 应用程序使用以下代码在 *test2* 应用程序下运行：

  ```
  public void Configuration(IAppBuilder app)
          {
              // For more information on how to configure your application, visit https://go.microsoft.com/fwlink/?LinkID=316888
              app.SetDefaultSignInAsAuthenticationType(CookieAuthenticationDefaults.AuthenticationType);
              app.UseCookieAuthentication(new CookieAuthenticationOptions());
              app.UseOpenIdConnectAuthentication(
                  new OpenIdConnectAuthenticationOptions
                  {
                      // Sets the ClientId, authority, RedirectUri as obtained from web.config
                      ClientId = clientId,
                      Authority = authority,
                      RedirectUri = "https://mysite/test2",
                      // PostLogoutRedirectUri is the page that users will be redirected to after sign-out. In this case, it is using the home page
                      PostLogoutRedirectUri = redirectUri,
                      Scope = OpenIdConnectScope.OpenIdProfile,
                      // ResponseType is set to request the id_token - which contains basic information about the signed-in user
                      ResponseType = OpenIdConnectResponseType.IdToken,
                      // ValidateIssuer set to false to allow personal and work accounts from any organization to sign in to your application
                      // To only allow users from a single organizations, set ValidateIssuer to true and 'tenant' setting in web.config to the tenant name
                      // To allow users from only a list of specific organizations, set ValidateIssuer to true and use ValidIssuers parameter

                      // OpenIdConnectAuthenticationNotifications configures OWIN to send notification of failed authentications to OnAuthenticationFailed method

                      Notifications = new OpenIdConnectAuthenticationNotifications
                      {
                          AuthenticationFailed = OnAuthenticationFailed
                      }

                  }
              );
          }
  ```
- 使用以下代码触发登录流：

  ```
  public void SignIn()
          {
              if (!Request.IsAuthenticated)
              {
                  HttpContext.GetOwinContext().Authentication.Challenge(
                      new AuthenticationProperties { RedirectUri = "/" },
                      OpenIdConnectAuthenticationDefaults.AuthenticationType);
              }
          }
  ```

此方案可能会导致身份验证无限循环，并生成多个 OpenIdConnect.nonce Cookie。 区别在于，ASP.NET 似乎未设置其经过身份验证的会话 Cookie。 若要解决此类方案中的问题，请在 OpenID Connect 初始化代码和 `Challenge` 方法中设置重定向 URL（请注意重定向 URL 中的尾部斜杠）：

```
app.UseOpenIdConnectAuthentication(
                new OpenIdConnectAuthenticationOptions
                {
                    // Sets the ClientId, authority, RedirectUri as obtained from web.config
                    ClientId = clientId,
                    Authority = authority,
                    RedirectUri = "https://mysite/test2/",
                    // PostLogoutRedirectUri is the page that users will be redirected to after sign-out. In this case, it is using the home page
                    PostLogoutRedirectUri = redirectUri,
                    Scope = OpenIdConnectScope.OpenIdProfile,
...
```

```
 public void SignIn()
        {
            if (!Request.IsAuthenticated)
            {
                HttpContext.GetOwinContext().Authentication.Challenge(
                    new AuthenticationProperties { RedirectUri = "/test2/" },
                    OpenIdConnectAuthenticationDefaults.AuthenticationType);
            }
        }
```

## 参考文献

- [使用 ASP.NET OWIN 和 OpenID Connect 进行无限重定向](https://varnerin.info/infinite-redirects-with-aspnet-owin-and-openid-connect/)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/asp-dot-net-application-infinite-sign-in-loop)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
