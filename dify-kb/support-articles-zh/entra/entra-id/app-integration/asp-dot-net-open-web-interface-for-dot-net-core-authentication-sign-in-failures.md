# 使用 Microsoft Entra ID 排查 ASP.NET OWIN 和 ASP.NET 核心身份验证登录失败问题

## 概要

开发 ASP.NET Open Web Interface for .NET （OWIN） 或 ASP.NET Core Authentication Web 应用程序并将其与 Microsoft Entra ID 集成时，在登录过程中遇到一些问题，而不会出现任何错误消息或提示问题。 本文不侧重于直接解决登录失败的解决方案，但旨在帮助你公开隐藏的错误消息，以指导你解决问题。

注释

本文假定您使用自己的代码来执行到 Microsoft Entra ID 的身份验证。 如果使用 Azure 应用服务或 Azure Functions 身份验证和授权功能，本文不适用于你的方案。

## 症状

你可能会看到一些常见的登录失败行为，如下所示：

- 您的 Web 应用程序与 Microsoft Entra ID 之间出现了死循环。
- 登录到 Microsoft Entra ID 后，会重定向到 Web 应用程序，就好像从未登录过一样。
- 您进入了一个错误页面，但它没有提供有用的错误信息。

## 使用 OnAuthenticationFailed 事件公开隐藏错误

若要在登录过程中公开隐藏的错误，请使用该 `OnAuthenticationFailed` 事件。

### 对于 ASP.NET OWIN

确保`AuthenticationFailed`文件中事件的代码遵循以下结构：

```
public void ConfigureAuth(IAppBuilder app)
{
    app.SetDefaultSignInAsAuthenticationType(CookieAuthenticationDefaults.AuthenticationType);

    app.UseCookieAuthentication(new CookieAuthenticationOptions());

    app.UseOpenIdConnectAuthentication(
        new OpenIdConnectAuthenticationOptions
        {
            ResponseType = OpenIdConnectResponseType.CodeIdToken,
            ClientId = clientId,
            Authority = Authority,
           //...

            Notifications = new OpenIdConnectAuthenticationNotifications()
            {
                // If there is a code in the OpenID Connect response, redeem it for an access token
                AuthorizationCodeReceived = (context) =>
                {
                    // ...
                },

                // On Authentication Failed
                AuthenticationFailed = (context) =>
                {
                    String ErrorMessage = context.Exception.Message;
                    String InnerErrorMessage = String.Empty;

                    String RedirectError = String.Format("error_message={0}", ErrorMessage);

                    if (context.Exception.InnerException != null)
                    {
                        InnerErrorMessage = context.Exception.InnerException.Message;
                        RedirectError = String.Format("{0}&inner_error={1}", RedirectError, InnerErrorMessage);
                    }

                    // or you can just throw it
                  // throw new Exception(RedirectError);

                    RedirectError = RedirectError.Replace("\r\n", "  ");

                    context.Response.Redirect("/?" + RedirectError);
                    context.HandleResponse();
                    return Task.FromResult(0);
                }
            }

      });

// ...
```

### 对于 ASP.NET Core

确保`AuthenticationFailed`文件中事件的代码遵循以下结构：

```
public void ConfigureServices(IServiceCollection services)
{
    services.Configure<CookiePolicyOptions>(options =>
    {
        // ...
    });

    services.AddAuthentication(AzureADDefaults.AuthenticationScheme)
        .AddAzureAD(options => Configuration.Bind("AzureAd", options));

    // ...

    services.Configure<OpenIdConnectOptions>(AzureADDefaults.OpenIdScheme, options =>
    {
    options.Authority = options.Authority;

    // Token Validation
    options.TokenValidationParameters.IssuerValidator = AadIssuerValidator.ValidateAadIssuer;

    // Response type
    options.ResponseType = "id_token code";

    // On Authorization Code Received
    options.Events.OnAuthorizationCodeReceived = async context =>
    {
        // ...
    };

    // On Authentication Failed
    options.Events.OnAuthenticationFailed = async context =>
    {
        String ErrorMessage = context.Exception.Message;
        String InnerErrorMessage = String.Empty;

        String RedirectError = String.Format("?error_message={0}", ErrorMessage);

        if (context.Exception.InnerException != null)
        {
            InnerErrorMessage = context.Exception.InnerException.Message;
            RedirectError = String.Format("{0}&inner_error={1}", RedirectError, InnerErrorMessage);
        }

       // or you can just throw it
       // throw new Exception(RedirectError);

        RedirectError = RedirectError.Replace("\r\n", "  ");

        context.Response.Redirect(RedirectError);
        context.HandleResponse();
    };

    // ...
```

可以修改此结构以将错误消息发送到日志或将其发送到自定义错误页。 至少应在浏览器的地址栏中显示错误消息。

![显示浏览器地址栏中错误消息的屏幕截图。](media/asp-dot-net-open-web-interface-for-dot-net-core-authentication-sign-in-failures/error-message-in-address-bar.png)

如果存在无限循环，则错误消息应在 Fiddler 捕获中可见。

![显示 Fiddler 捕获中的错误消息的屏幕截图。](media/asp-dot-net-open-web-interface-for-dot-net-core-authentication-sign-in-failures/error-message-in-fiddler-capture.png)

有关使用 Fiddler 的详细信息，请参阅 [使用 Fiddler 收集用于 Microsoft Entra ID 应用的 HTTPS 流量](capture-https-traffic-fiddler-entra-id-app)。

## Microsoft Entra 身份验证和授权错误代码

有关Microsoft Entra 身份验证和授权错误的列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/entra/identity-platform/reference-error-codes)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/asp-dot-net-open-web-interface-for-dot-net-core-authentication-sign-in-failures)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
