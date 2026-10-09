# 使用 Serilog 排查由 Microsoft Entra 保护的 Web API 身份验证或授权问题

## 概要

当 Web API 应用程序调用受Microsoft Entra ID 保护的 Web API 时，可能会由于 JwtBearer 事件验证失败而发生身份验证或授权错误。 为了解决此问题，本文介绍了名为 [Net6WebAPILogging](https://github.com/bachoang/Net6WebAPILogging) 的示例 Web API 应用程序，用于设置和收集 JwtBearer 事件的日志。

## Net6WebAPILogging 示例应用程序

此示例 Web API 应用程序假定已在 Microsoft Entra ID 中注册了 Web API。 它使用 Microsoft .NET 6 Framework 和 [Microsoft Identity Web](/zh-cn/entra/msal/dotnet/microsoft-identity-web/) NuGet 包。

它使用以下方法来设置和收集 JwtBearer 事件的日志：

- 使用 [JwtBearerEvents 类](/zh-cn/dotnet/api/microsoft.aspnetcore.authentication.jwtbearer.jwtbearerevents) 配置中间件事件。 JWT 持有者令牌可能无法验证`OnTokenValidated`、`OnMessageReceived``OnAuthenticationFailed`和`OnChalleenge`事件。
- [为 JwtBearer 事件设置日志记录](#set-up-logging-for-jwtbearer-events)。
- 使用 [Serilog](https://serilog.net/) 框架将 `Debug` 输出记录到控制台窗口和 **appsettings.json文件中指定**  路径的本地文件。

## 运行示例应用程序

若要运行示例应用程序，必须执行以下步骤：

### 步骤 1：为受保护的 Web API 配置应用程序 ID URI

若要为 Web API 添加应用程序 ID URI，请执行以下步骤：

1. 在 Azure 门户中，导航到 Web API 的应用注册。
2. 在“管理”下选择“公开 API”。
3. 在页面顶部，选择“添加”按钮，该按钮位于“应用程序 ID URI”旁边。 默认值为 `api://<application-client-id>`。

   ![显示如何在应用注册中设置应用程序 ID URI 的屏幕截图。](media/serilog-protected-web-api-authentication-authorization-errors/application-id-uri.png)
4. 选择**“保存”**。

### 步骤 2：更改示例应用程序配置

使用自己的应用注册信息更改 `AzureAd` 文件中部分中的以下信息：

```
"AzureAd": {
    "Instance": "https://login.microsoftonline.com/",
    "Domain": "<tenant name>.onmicrosoft.com", // for example contoso.onmicrosoft.com
    "TenantId": "<tenant ID>",
    "ClientId": "<application-client-id>"
  },
```

### 步骤 3：更改示例应用程序代码

更改 `ValidAudiences``ValidIssuers`[Program.cs](/zh-cn/dotnet/api/microsoft.identitymodel.tokens.tokenvalidationparameters) 文件中 **TokenValidationParameters** 类的属性。

### 步骤 4：配置 Serilog

在`Serilog` 文件中的  节中配置 Serilog，如下所示：

```
  "Serilog": {
    "MinimumLevel": {
      "Default": "Information",
      "Override": {
        "Microsoft": "Debug",
        "Microsoft.Hosting.Lifetime": "Information"
      }
    },
```

## 为 JwtBearer 事件设置日志记录

下面是演示如何为上述事件设置日志记录的示例 **Program.cs** 文件：

```
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.Identity.Web;
using Microsoft.IdentityModel.Logging;
using System.Diagnostics;
using Serilog;

// https://github.com/datalust/dotnet6-serilog-example

Log.Logger = new LoggerConfiguration()
    .WriteTo.Console()
    .CreateBootstrapLogger();

Log.Information("starting up");
try
{
    var builder = WebApplication.CreateBuilder(args);

    builder.Host.UseSerilog((ctx, lc) => lc
        .WriteTo.Console()
        .ReadFrom.Configuration(ctx.Configuration));

    // Add services to the container.
    builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
        .AddMicrosoftIdentityWebApi(builder.Configuration.GetSection("AzureAd"));

    // Enable PII for logging
    IdentityModelEventSource.ShowPII = true;
    // Configure middleware events
    builder.Services.Configure<JwtBearerOptions>(JwtBearerDefaults.AuthenticationScheme, options =>
    {
        options.TokenValidationParameters = new Microsoft.IdentityModel.Tokens.TokenValidationParameters
        {
            ValidAudiences = new List<string> { "api://<application-client-id>", "<application-client-id>" },
            ValidIssuers = new List<string> { "https://sts.windows.net/<tenant ID>/", "https://login.microsoftonline.com/<tenant ID>/v2.0" }
        };
        options.Events = new JwtBearerEvents
        {
            OnTokenValidated = ctx =>
            {
                string message = "[OnTokenValidated]: ";
                message += $"token: {ctx.SecurityToken.ToString()}";
                Log.Information(message); 
                return Task.CompletedTask;
            },
            OnMessageReceived = ctx =>
            {
                string message = "[OnMessageReceived]: ";
                ctx.Request.Headers.TryGetValue("Authorization", out var BearerToken);
                if (BearerToken.Count == 0)
                    BearerToken = "no Bearer token sent\n";
                message += "Authorization Header sent: " + BearerToken + "\n";
                Log.Information(message);
                return Task.CompletedTask;
            },
            OnAuthenticationFailed = ctx =>
            {
                ctx.Response.StatusCode = StatusCodes.Status401Unauthorized;
                string message = $"[OnAuthenticationFailed]: {ctx.Exception.ToString()}";
                Log.Error(message);
                // Debug.WriteLine("[OnAuthenticationFailed]: Authentication failed with the following error: ");
                // Debug.WriteLine(ctx.Exception);
                return Task.CompletedTask;
            },
            OnChallenge = ctx =>
            {
                // Debug.WriteLine("[OnChallenge]: I can do stuff here! ");
                Log.Information("[OnChallenge]");
                return Task.CompletedTask;
            },
            OnForbidden = ctx =>
            {
                Log.Information("[OnForbidden]");
                return Task.CompletedTask;
            }
        };
    });

    builder.Services.AddControllers();
    // Learn more about configuring Swagger/OpenAPI at https://aka.ms/aspnetcore/swashbuckle
    // builder.Services.AddEndpointsApiExplorer();
    // builder.Services.AddSwaggerGen();

    var app = builder.Build();

    app.UseSerilogRequestLogging();
    // Configure the HTTP request pipeline.
    if (app.Environment.IsDevelopment())
    {
        // app.UseSwagger();
        // app.UseSwaggerUI();
        // do something
    }

    app.UseHttpsRedirection();

    app.UseAuthentication();
    app.UseAuthorization();

    app.MapControllers();

    app.Run();
}
catch (Exception ex)
{
    Log.Fatal(ex, "Unhandled exception");
}
finally
{
    Log.Information("Shut down complete");
    Log.CloseAndFlush();
}
```

## 参考文献

[教程：使用 Microsoft 标识平台生成和保护 ASP.NET Core Web API](/zh-cn/entra/identity-platform/tutorial-web-api-dotnet-core-build-app)

**第三方信息免责声明**

本文讨论的第三方产品由独立于微软的公司制造。 Microsoft对这些产品的性能或可靠性不作任何明示或暗示的保证。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/serilog-protected-web-api-authentication-authorization-errors)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
