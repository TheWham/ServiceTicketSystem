# ASP.NET Core Web API 中使用 Microsoft Entra ID 时出现的 401 未授权错误

## 概要

本文提供指导，帮助您使用 JwtBearerEvents 以捕获详细日志，从而在调用使用 Microsoft Entra ID 身份验证保护的 ASP.NET Core Web API 时，排除“401 未授权”错误。

## 症状

使用 `[Authorize]` 属性 [来保护 ASP.NET Core Web API](/zh-cn/entra/identity-platform/tutorial-web-api-dotnet-core-build-app?tabs=workforce-tenant)，如下所示：

```
[Authorize]
public class MyController : ControllerBase
{
    ...
}
```

或

```
public class MyController : ControllerBase
{
   [Authorize]
   public ActionResult<string> Get(int id)
   {
       return "value";
   }
   ...
}
```

调用 Web API 时，将返回“401 未授权”响应，但消息不包含错误详细信息。

## 原因

在以下情况下，API 可能会返回“401 未授权”响应：

- 请求中未包含有效的“Authorization: Bearer”令牌标头。
- 令牌已过期或不正确：
  - 令牌是针对其他资源颁发的。
  - 令牌声明不符合应用程序的令牌验证条件，如 [JwtBearerOptions.TokenValidationParameters](/zh-cn/dotnet/api/microsoft.aspnetcore.authentication.jwtbearer.jwtbeareroptions.tokenvalidationparameters) 类中定义。

## 解决方案

若要调试并解决“401 未授权”错误，请使用 `JwtBearerEvents` 回调捕获和记录详细的错误信息。 按照以下步骤实现自定义错误处理机制。

该 `JwtBearerEvents` 类具有以下回调属性（按以下顺序调用），可帮助你调试这些“401 拒绝访问”或“UnAuthorization”问题：

- [`OnMessageRecieved`](/zh-cn/dotnet/api/microsoft.aspnetcore.authentication.jwtbearer.jwtbearerevents.onmessagereceived#Microsoft_AspNetCore_Authentication_JwtBearer_JwtBearerEvents_OnMessageReceived) 为每个请求首先调用 。
- [`OnAuthenticationFailed`](/zh-cn/dotnet/api/microsoft.aspnetcore.authentication.jwtbearer.jwtbearerevents.onauthenticationfailed) 如果令牌未通过应用程序的令牌验证条件，则调用 。
- [`OnChallenge`](/zh-cn/dotnet/api/microsoft.aspnetcore.authentication.jwtbearer.jwtbearerevents.onchallenge) 在返回“401”响应之前是最后一个被调用的。

### 步骤 1：启用 PII 日志记录

默认情况下，禁用个人身份信息（PII）日志记录。 在用于调试的 Startup.cs 文件的 **Configure** 方法中启用它。

谨慎

仅在开发环境中使用“Microsoft.IdentityModel.Logging.IdentityModelEventSource.ShowPII = true”进行调试。 请勿在生产环境中使用它。

```
public void Configure(IApplicationBuilder app, IHostingEnvironment env)
{
    if (env.IsDevelopment())
    {
        app.UseDeveloperExceptionPage();
    }
    else
    {
        // The default HSTS value is 30 days. You might want to change this value for production scenarios. See https://aka.ms/aspnetcore-hsts.
        app.UseHsts();
    }
    // turn on PII logging
    Microsoft.IdentityModel.Logging.IdentityModelEventSource.ShowPII = true;

    app.UseHttpsRedirection();
    app.UseAuthentication();
    app.UseMvc();
}
```

### 步骤 2：创建用于设置异常消息格式的实用工具方法

添加一种方法来整理并展平任何异常信息，以提高可读性。

```
public static string FlattenException(Exception exception)
{
    var stringBuilder = new StringBuilder();
    while (exception != null)
    {
        stringBuilder.AppendLine(exception.Message);
        stringBuilder.AppendLine(exception.StackTrace);
        exception = exception.InnerException;
    }
    return stringBuilder.ToString();
}
```

### 步骤 3：实现 JwtBearerEvents 的回调函数

在 `JwtBearerEvents` 方法的 `ConfigureServices` 中配置回调，以处理身份验证事件并记录错误详细信息：

```
public void ConfigureServices(IServiceCollection services)
{
....
    .AddJwtBearer(options =>
    {
        options.Authority = "https://login.microsoftonline.com/<Tenant>.onmicrosoft.com";
        // if you intend to validate only one audience for the access token, you can use options.Audience instead of
        // using options.TokenValidationParameters which allow for more customization.
        // options.Audience = "10e569bc5-4c43-419e-971b-7c37112adf691";

        options.TokenValidationParameters = new Microsoft.IdentityModel.Tokens.TokenValidationParameters
        {
            ValidAudiences = new List<string> { "<Application ID URI>", "10e569bc5-4c43-419e-971b-7c37112adf691" },
            ValidIssuers = new List<string> { "https://sts.windows.net/<Directory ID>/", "https://sts.windows.net/<Directory ID>/v2.0" }
        };
                
        options.Events = new JwtBearerEvents
        {
            OnAuthenticationFailed = ctx =>
            {
                ctx.Response.StatusCode = StatusCodes.Status401Unauthorized;
                message += "From OnAuthenticationFailed:\n";
                message += FlattenException(ctx.Exception);
                return Task.CompletedTask;
            },

            OnChallenge = ctx =>
            {
                message += "From OnChallenge:\n";
                ctx.Response.StatusCode = StatusCodes.Status401Unauthorized;
                ctx.Response.ContentType = "text/plain";
                return ctx.Response.WriteAsync(message);
            },

            OnMessageReceived = ctx =>
            {
                message = "From OnMessageReceived:\n";
                ctx.Request.Headers.TryGetValue("Authorization", out var BearerToken);
                if (BearerToken.Count == 0)
                    BearerToken = "no Bearer token sent\n";
                message += "Authorization Header sent: " + BearerToken + "\n";
                return Task.CompletedTask;
            },
#For completeness, the sample code also implemented the OnTokenValidated property to log the token claims. This method is invoked when authentication is successful
            OnTokenValidated = ctx =>
            {
                Debug.WriteLine("token: " + ctx.SecurityToken.ToString());
                return Task.CompletedTask;
            }
        };
    });
...
}
```

### 示例结果

实现 `JwtBearerEvents` 回调时，如果出现“401 未授权”错误，响应输出应包括如下示例所示的详细信息：

```
OnMessageRecieved:

Authorization Header sent: no Bearer token sent.
```

如果使用 API 开发工具调试请求，应会收到错误详细信息，如以下屏幕截图所示。

[![API 开发工具中错误详细信息的屏幕截图。](media/401-unauthorized-aspnet-core-web-api/wrong-token.png)](media/401-unauthorized-aspnet-core-web-api/wrong-token.png#lightbox)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/401-unauthorized-aspnet-core-web-api)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
