# 没有持久性令牌缓存的 Web 应用程序中出现“未将帐户或登录提示传递给 AcquireTokenSilent”错误

## 概要

本文提供了有关使用Microsoft身份验证库（MSAL）或Microsoft标识 Web 的 Web 应用程序中发生的“未将帐户或登录提示传递给 AcquireTokenSilent”错误的解决方案。

## 症状

假设您的 Web 应用程序使用 MSAL 或 Microsoft Identity Web 对用户进行身份验证，并且不使用持久性令牌缓存。 当 MSAL 尝试从其令牌缓存中以无提示方式拉取用户帐户并获取令牌时，将显示以下错误消息：

> 未将帐户或登录提示传递给 AcquireTokenSilent

## 原因

出现此问题是因为 MSAL 依据现有的身份验证 Cookie 在令牌缓存中寻找一个已不存在的帐户。 身份验证 Cookie 仅在交互式登录后创建，并包含有关用户的信息。 此问题发生在以下方案中：

- Web 应用程序已重启。
- 由于内存使用率过高或经过一段时间未使用，内存已被清除。
- MSAL 具有默认缓存大小限制，可自动删除较旧的条目。

## 解决方案 1（建议）：实现持久性令牌缓存

可以在持久位置（如 SQL Server 或基于文件的存储）中实现持久性令牌缓存。 持久性令牌缓存可确保即使应用程序重启或清除内存，令牌也会保留。 有关如何实现自定义持久令牌缓存的详细信息，请参阅 [令牌缓存序列化](/zh-cn/entra/msal/dotnet/how-to/token-cache-serialization)。

## 解决方案 2：拒绝身份验证 Cookie

可以实现 Cookie 身份验证事件，以验证当前登录的用户是否存在于 MSAL 令牌缓存中。 如果用户不存在，请拒绝身份验证 Cookie 并强制当前用户重新登录。

### 对于使用 MSAL 的 ASP.NET 网络应用程序

创建 Cookie 身份验证事件：

```
app.UseCookieAuthentication(new CookieAuthenticationOptions
{
    Provider = new CookieAuthenticationProvider()
    {
        OnValidateIdentity = async context =>
        {
            IConfidentialClientApplication clientApp = MsalAppBuilder.BuildConfidentialClientApplication();
        
                var signedInUserIdentity = new ClaimsPrincipal(context.Identity);
        
                if (await clientApp.GetAccountAsync(signedInUserIdentity.GetAccountId()) == null)
        
                {
        
                    context.RejectIdentity();
        
                }
    
        }
    
    }

});
```

注释

若要实现 Cookie 身份验证事件，Web 应用程序必须安装以下帮助程序类和 `Microsoft.Identity.Web.TokenCache` NuGet 包：

- `MsalAppBuilder.cs`
- `AuthenticationConfig.cs`

### 对于使用 MSAL 的 ASP.NET Core Web 应用程序

1. 创建自定义 Cookie 身份验证事件：

   ```
   using Microsoft.AspNetCore.Authentication.Cookies;
   using Microsoft.Extensions.DependencyInjection;
   using Microsoft.Identity.Client;
   using System.Threading.Tasks;
   using System.Security.Claims;

   namespace SampleApp.Services
   {
       internal class RejectSessionCookieWhenAccountNotInCacheEvents : CookieAuthenticationEvents
       {
           public async override Task ValidatePrincipal(CookieValidatePrincipalContext context)
           {
               var msalInstance = context.HttpContext.RequestServices.GetRequiredService();
               IConfidentialClientApplication msalClient = msalInstance.GetClient();

                       var accounts = await msalClient.GetAccountsAsync();

                       var account = await msalClient.GetAccountAsync(accounts.FirstOrDefault());

                       if (account == null)

                       {

                           context.RejectPrincipal();

                       }

                       await base.OnValidatePrincipal(context);

               }

       }

   }
   ```
2. 注册自定义 Cookie 身份验证事件：

   ```
   Services.Configure<CookieAuthenticationOptions>(cookieScheme, options=>options.Events=new RejectSessionCookieWhenAccountNotInCacheEvents());
   ```

### 对于使用 Microsoft 身份识别的网络应用

Microsoft Identity Web 提供用于管理令牌缓存的内置机制。 有关详细信息，请参阅 [管理增量同意和条件访问](https://github.com/AzureAD/microsoft-identity-web/wiki/Managing-incremental-consent-and-conditional-access)。 如果本文档不能帮助你解决问题，可以通过自定义的 Cookie 身份验证事件手动清除身份验证 Cookie：

1. 创建自定义 Cookie 身份验证事件：

   ```
   using Microsoft.AspNetCore.Authentication.Cookies;
   using Microsoft.Extensions.DependencyInjection;
   using Microsoft.Identity.Client;
   using Microsoft.Identity.Web;
   using System;
   using System.Collections.Generic;
   using System.Linq;
   using System.Threading.Tasks;

   namespace SampleApp.Services
   {
       internal class RejectSessionCookieWhenAccountNotInCacheEvents : CookieAuthenticationEvents
       {
           public async override Task ValidatePrincipal(CookieValidatePrincipalContext context)
           {
               try
               {
                   var tokenAcquisition = context.HttpContext.RequestServices.GetRequiredService();
                   string token = await tokenAcquisition.GetAccessTokenForUserAsync(
                   scopes: new[] { "profile" },
                   user: context.Principal);
               }
               catch (MicrosoftIdentityWebChallengeUserException ex)
               when (AccountDoesNotExistInTokenCache(ex))
               {
                   context.RejectPrincipal();
               }
           }
           /// <summary>
           /// Is the exception due to no account in the token cache?
           /// </summary>
           /// <param name="ex">Exception thrown by <see cref="ITokenAcquisition"/>.GetTokenForXX methods.</param>
           /// <returns>A boolean indicating if the exception relates to the absence of an account in the cache.</returns>
           private static bool AccountDoesNotExistInTokenCache(MicrosoftIdentityWebChallengeUserException ex)
           {
               return ex.InnerException is MsalUiRequiredException

                      && (ex.InnerException as MsalUiRequiredException).ErrorCode == "user_null";

           }

       }

   }
   ```
2. 注册自定义 Cookie 身份验证事件：

   ```
   // Add Microsoft Identity Web
   services.AddAuthentication(OpenIdConnectDefaults.AuthenticationScheme)
                       .AddMicrosoftIdentityWebApp(Configuration.GetSection("AzureAd"))
                           .EnableTokenAcquisitionToCallDownstreamApi(initialScopes)
                              .AddMicrosoftGraph(Configuration.GetSection("GraphBeta"))
                              .AddInMemoryTokenCaches();

   // Register the Custom Cookie Authentication event
   Services.Configure<CookieAuthenticationOptions>(cookieScheme, options=>options.Events=new RejectSessionCookieWhenAccountNotInCacheEvents());
   ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/no-account-login-hint-passed-acquire-token-silent)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
