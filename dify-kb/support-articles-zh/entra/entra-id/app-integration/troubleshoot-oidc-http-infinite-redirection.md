# 排查 OIDC 应用与 Entra ID 之间的无限重定向问题

## 概要

本文介绍 OpenID Connect （OIDC） 应用程序和 Microsoft Entra ID 之间存在的无限重定向问题。

## 现象

当你浏览到使用 OpenID Connect（OIDC）应用生成的网站并Microsoft Entra ID 时，浏览器将输入一个无限循环，该循环可在网站与Microsoft Entra ID 身份验证过程之间形成。

使用 HTTP 协议浏览网站时，会出现此问题。 使用 HTTPS 时，不会出现问题。

## 原因

`.AspNet.Cookies`由于 Cookie 的安全属性，Cookie 不会在 HTTP 请求中发送。

## 解决方案：强制实施 HTTPS 导航

若要解决此问题，请为网站强制实施 HTTPS 导航。 对于需要身份验证的站点，始终建议使用 HTTPS。

## 解决方法

如果你的方案需要通过 HTTP 进行初始导航，则可以自定义 Cookie 身份验证中间件，以允许 HTTP 和 HTTPS 方案的身份验证 AspNet Cookie，方法是将属性设置为`CookieSecure``CookieSecureOption.Never`，如以下`Startup.Auth.cs`文件中所示。

注意

不建议将此解决方法用于生产环境，因为它通过允许通过 HTTP 发送 Cookie 来损害安全性。

```
public void ConfigureAuth(IAppBuilder app)
        {
            app.SetDefaultSignInAsAuthenticationType(CookieAuthenticationDefaults.AuthenticationType);
            app.UseCookieAuthentication(new CookieAuthenticationOptions
            {
                CookieSecure = CookieSecureOption.Never
            });

            app.UseOpenIdConnectAuthentication(
                new OpenIdConnectAuthenticationOptions
                {
                    ClientId = clientId,
                    Authority = authority,

}
        }
```

此 ASP.NET 安全博客文章（问题 #219）[中还](https://github.com/aspnet/Security/issues/219)讨论了此问题。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/troubleshoot-oidc-http-infinite-redirection)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
