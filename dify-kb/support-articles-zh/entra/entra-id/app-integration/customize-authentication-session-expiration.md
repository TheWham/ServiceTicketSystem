# 自定义中间件身份验证票证以延长用户登录持续时间

## 概要

本文提供了有关如何将 ASP.NET 或 ASP.NET 核心应用会话配置为持续时间比 Microsoft Entra ID 令牌更长的指导。

默认情况下，Microsoft Entra ID 令牌（ID 令牌、访问令牌和 SAML 令牌）在一小时后过期。 此外，默认情况下，ASP.NET 和 ASP.NET 核心中间件将其身份验证票证设置为这些令牌的过期时间。 如果不希望 Web 应用程序将用户重定向到 Microsoft Entra ID 以让他们再次登录，则可以自定义中间件身份验证票证。

此自定义还可以帮助解决与 AJAX 相关的问题，例如 coss-origin 资源共享（CORS）错误来 login.microsoftonline.com。 当应用同时充当 Web 应用程序和 Web API 时，通常会发生这些问题。

## 对于 ASP.NET

在 `ConfigureAuth` 文件中的 `Startup.Auth.cs` 方法里，将 `app.UseCookieAuthentication()` 方法更新为：

```
app.UseCookieAuthentication(new CookieAuthenticationOptions()
{
  CookieManager = new Microsoft.Owin.Host.SystemWeb.SystemWebChunkingCookieManager(),
  Provider = new CookieAuthenticationProvider()
  {
    OnResponseSignIn = (context) =>
    {
      context.Properties.ExpiresUtc = DateTimeOffset.UtcNow.AddHours(12);
    }
  }
});
```

然后，将令牌生存期与 Web 应用分离：

```
app.UseOpenIdConnectAuthentication(
                new OpenIdConnectAuthenticationOptions
                {
                    UseTokenLifetime = false,
                    ...
```

## 对于 ASP.NET Core

在 ASP.NET Core 中，必须添加 `OnTokenValidated` 事件以更新票证属性。 此添加设置在应用程序重定向到 Microsoft Entra ID 以进行重新身份验证之前发生的票证过期时间。

```
services.Configure<OpenIdConnectOptions>(AzureADDefaults.OpenIdScheme, options =>
{
    // decouple the token lifetime from the Web App
    options.UseTokenLifetime = false;

    // other configurations...
    // ...

    var onTokenValidated = options.Events.OnTokenValidated;
    options.Events ??= new OpenIdConnectEvents();
    options.Events.OnTokenValidated = async context =>
    {
        await onTokenValidated(context);
        context.Properties.ExpiresUtc = DateTimeOffset.UtcNow.AddHours(12);
    };
});
```

### 例子

下面是如何进行此设置的几个示例：

如果您使用类似于以下示例的代码来添加 Microsoft Entra ID 身份验证：

```
services.AddAuthentication(AzureADDefaults.AuthenticationScheme)
  .AddAzureAD(options => Configuration.Bind("AzureAd", options))
```

然后添加以下代码：

```
services.Configure<OpenIdConnectOptions>(AzureADDefaults.OpenIdScheme, options =>
{
  // decouple the id_token lifetime from the Web App
  options.UseTokenLifetime = false;

  //…

    var onTokenValidated = options.Events.OnTokenValidated;
    options.Events ??= new OpenIdConnectEvents();
    options.Events.OnTokenValidated = async context =>
    {
        await onTokenValidated(context);
        context.Properties.ExpiresUtc = DateTimeOffset.UtcNow.AddHours(12);
    };
});
```

Startup.cs中的配置应类似于以下示例：

```
public void ConfigureServices(IServiceCollection services)
{
  //...

  services.AddAuthentication(AzureADDefaults.AuthenticationScheme)
    .AddAzureAD(options => Configuration.Bind("AzureAd", options))
    .AddCookie();

  //...

  services.Configure<OpenIdConnectOptions>(AzureADDefaults.OpenIdScheme, options =>
  {
    // decouple the token lifetime from the Web App
    options.UseTokenLifetime = false;

    //...
    var onTokenValidated = options.Events.OnTokenValidated;
    options.Events ??= new OpenIdConnectEvents();
    options.Events.OnTokenValidated = async context =>
    {
        await onTokenValidated(context);
        context.Properties.ExpiresUtc = DateTimeOffset.UtcNow.AddHours(12);
    };
  });

  //...
}
```

如果您使用`Microsoft.Identity.Web`来添加Microsoft Entra ID配置：

```
//…
using Microsoft.Identity.Web;
//…
public class Startup
{
  // ...
  public void ConfigureServices(IServiceCollection services)
  {
    // ...
    services.AddAuthentication(OpenIdConnectDefaults.AuthenticationScheme)
      .AddMicrosoftIdentityWebApp(options =>
      {
        Configuration.Bind("AzureAD", options);

        // decouple the token lifetime from the Web App
        options.UseTokenLifetime = false;

        var onTokenValidated = options.Events.OnTokenValidated;
        options.Events ??= new OpenIdConnectEvents();
     
        options.Events.OnTokenValidated = async context =>
        {
            await onTokenValidated(context);
            context.Properties.ExpiresUtc = DateTimeOffset.UtcNow.AddHours(12);
        };
      });
    // ...
}			
```

如果要实现自己的自定义 `OpenIdConnectOptions` 来配置 Microsoft Entra ID 身份验证：

```
services.Configure<OpenIdConnectOptions>(options =>
{
  //…
  options.Events.OnTokenValidated = async context =>
  {
    context.Properties.ExpiresUtc = DateTimeOffset.UtcNow.AddHours(12);
  };
});
```

如果要集成 ASP.NET Core WS-Fed 应用程序：

```
public void ConfigureServices(IServiceCollection services)
{
  services.AddAuthentication(WsFederationDefaults.AuthenticationScheme)  
    .AddCookie()
    .AddWsFederation(options =>
    {
      options.SignInScheme = CookieAuthenticationDefaults.AuthenticationScheme;

      // decouple the token lifetime from the Web App
      options.UseTokenLifetime = false;

      // MetadataAddress for your Azure Active Directory instance.
      options.MetadataAddress = "https://login.microsoftonline.com/common/federationmetadata/2007-06/federationmetadata.xml";

      // Wtrealm is the app's identifier in the Active Directory instance.
      // For ADFS, use the relying party's identifier, its WS-Federation Passive protocol URL:
      options.Wtrealm = "https://localhost:44307/";

      // For AAD, use the Application ID URI from the app registration's Overview blade:
      options.Wtrealm = "https://contoso.onmicrosoft.com/wsfedapp";

      // Set the Authentication Ticket to expire at a custom time      
      var onTokenValidated = options.Events.OnTokenValidated;
      options.Events ??= new OpenIdConnectEvents();
      
      options.Events.OnSecurityTokenValidated = async context =>
      {
        context.Properties.ExpiresUtc = DateTimeOffset.UtcNow.AddHours(12);
      }
```

## 详细信息

这些设置控制认证凭证的过期时间，该凭证确定用户保持登录的一段时间。 可以将此过期时间配置为符合要求。

注释

如果您修改票证有效期，即使在 Microsoft Entra ID 中已删除或禁用用户，他们仍可能可以访问您的应用程序。 在票证过期之前，此条件保持不变。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/customize-authentication-session-expiration)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
