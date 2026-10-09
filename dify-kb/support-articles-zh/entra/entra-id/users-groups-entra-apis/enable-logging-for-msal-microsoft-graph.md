# 如何为 MSAL.NET 和 Microsoft Graph SDK 启用日志记录

[Microsoft Graph SDK](/zh-cn/graph/sdks/sdks-overview) 能够记录完整的 HTTP 请求和响应。 此日志记录机制的工作方式是通过实现自定义 [HttpClient 消息处理程序](https://visualstudiomagazine.com/articles/2014/08/01/creating-custom-httpclient-handlers.aspx) 来截获客户端应用程序和 Microsoft Graph 服务之间的每个 HTTP 请求和响应。 除了将`GraphServiceClient`类挂接到处理管道来执行请求和响应跟踪之外，还可以配置代理信息。 有关详细信息，请参阅 [自定义 Microsoft Graph SDK 服务客户端](/zh-cn/graph/sdks/customize-client?tabs=csharp)。 MSAL.NET 用于 `GraphServiceClient` 类的身份验证提供程序中。 因此， [在此库中登录](/zh-cn/azure/active-directory/develop/msal-logging-dotnet) 可提供对身份验证失败的宝贵见解。

本文介绍如何使用 [.NET Core 3.0 控制台应用程序示例](https://github.com/bachoang/MSGraphLoggingSample)为 MSAL.NET 和 Microsoft Graph SDK 启用日志记录。

## 日志记录技术

不同的日志记录方法被用于分别将日志条目写入 Azure Blob 存储，以记录 MSAL.NET 日志和 Microsoft Graph SDK 日志。 日志记录机制提供对 HTTP 请求和响应的见解，以及身份验证失败，这对调试和故障排除非常有用。

### MSAL.NET 日志记录

对于 MSAL.NET 日志记录， [Azure Blob 存储客户端 SDK](/zh-cn/azure/storage/blobs/storage-quickstart-blobs-dotnet) （v12）用于将日志条目写入 Azure Blob。

### Microsoft Graph SDK 日志记录

对于 Microsoft Graph SDK 日志记录，将使用 [Serilog](https://serilog.net/) 库。 Serilog 提供了各种日志记录提供程序，称为“接收器”，支持不同的日志记录环境，例如 Application Insight、DocumentDB 和事件中心。

在以下代码中，配置了三个日志记录接收器：控制台记录器、文件记录器和 Azure Blob 存储记录器。 无需使用这三个，并且可以添加新的一个或注释掉不需要的提供程序。

```
Log.Logger = new LoggerConfiguration()
.MinimumLevel.Debug()
.WriteTo.Console() // Serilog console logging
.WriteTo.File(LoggingLocalPath, rollingInterval: RollingInterval.Day) // Serilog file logging
.WriteTo.AzureBlobStorage(AzureStorageConnection, Serilog.Events.LogEventLevel.Verbose, MSGraphAzureBlobContainerName, MSGraphAzureBlobName) // Serilog Azure Blob Storage logging
.CreateLogger();
```

注释

当 Serilog Azure Blob Storage 日志接收器用于 MSAL.NET 和 Microsoft Graph SDK 的日志记录时，可能会遇到身份验证问题，即身份验证提示窗口无法显示。

## 运行示例应用程序的先决条件

在运行示例应用程序之前，请确保满足以下先决条件。

### 应用程序注册

1. 在 Microsoft Entra ID 中注册示例应用程序。

   在应用程序注册期间，在`http://localhost`平台下配置为重定向 URI。 .NET Core 应用程序需要此 URI。

   ![显示设置重定向 URI 的屏幕截图](media/enable-logging-for-msal-and-microsoft-graph/set-redirect-uri.png)
2. 在 **API 权限**中配置这些委托Microsoft Graph权限：

   - **User.Read.All**
   - Application.ReadWrite.All
3. 授予管理员对这些权限的许可，因为示例应用程序使用以下Microsoft Graph 请求获取登录用户信息并创建应用注册：

   - `GET https://graph.microsoft.com/beta/me`
   - `POST https://graph.microsoft.com/beta/applications`

注释

确保登录用户具有以下管理角色之一：应用程序开发人员、应用程序管理员、云应用程序管理员或全局管理员;否则，由于权限不足，应用程序创建可能会失败。 有关内置Microsoft Entra 角色的列表，请参阅 [Microsoft Entra 内置角色](/zh-cn/entra/identity/role-based-access-control/permissions-reference) 。

### Azure 存储

创建一个 Azure 存储帐户，用于将 MSAL.NET 和 Microsoft Graph SDK 日志存储为 Azure Blob。 若要读取/写入对 Azure 存储的访问权限，可以在**访问密钥****下使用 Key 1** 或 **Key 2** 中的连接字符串。

![显示“访问密钥”下的连接字符串的屏幕截图](media/enable-logging-for-msal-and-microsoft-graph/connection-string-under-access-keys.png)

### 应用程序代码

此 [GitHub 存储库](https://github.com/bachoang/MSGraphLoggingSample)中提供了完整的示例代码。 配置选项存储在以下 `appsettings.json` 文件中。 示例应用程序使用 [本文](../app-integration/get-signed-in-users-groups-in-access-token) 中的代码片段从 `appsettings.json` 文件读取配置设置。 它依赖于 Microsoft Graph beta 终结点，因此它引用 Microsoft.Graph.Beta 包;对于 v1 终结点，请使用 Microsoft.Graph 包。 有关详细信息，请参阅 [将 Microsoft Graph SDK 与 beta API 配合使用](/zh-cn/graph/sdks/use-beta)。

```
{
    "Azure": {
    "ClientId": "",
    "TenantId": "",
    "MSALAzureBlobContainerName": "msallogs",
    "MSALAzureBlobName": "MsalLog.txt",
    "MSGraphAzureBlobContainerName": "msgraphlogs",
    "MSGraphAzureBlobName": "{yyyy}-{MM}-{dd}-msgraphlog.txt",
    "LoggingLocalPath": "C:/temp/msgraphlog.txt",
    "AzureStorageConnection": "",
    "Scopes": [ "https://graph.microsoft.com/.default" ]
    }
}
```

示例应用程序使用两个`GET`和`POST`请求来显示完整的 HTTP 请求和响应的日志记录，包括标头和主体。 以下四个帮助程序函数用于获取每个部件的信息。 如果不需要相应的信息，则可以注释掉任何函数。

![显示四个帮助程序函数的屏幕截图](media/enable-logging-for-msal-and-microsoft-graph/helper-functions.png)

这些辅助函数在日志记录 `HttpClient` 消息处理程序中使用，如下所示。 在调用 `DelegatingHandler.SendAsync` 方法之前记录请求，并在调用后记录响应。

```
public class SeriLoggingHandler : DelegatingHandler
{
    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage httpRequest, CancellationToken cancellationToken)
        {
            HttpResponseMessage response = null;
            try
            {
                Log.Information("sending Graph Request");
                Log.Debug(GetRequestHeader(httpRequest));
                Log.Debug(GetRequestBody(httpRequest));
                response = await base.SendAsync(httpRequest, cancellationToken);
                Log.Information("Receiving Response:");
                Log.Debug(GetResponseHeader(response));
                Log.Debug(GetResponseBody(response));
            }
            catch (Exception ex)
            {
                Log.Error(ex, "Something went wrong");
                if (response.Content != null)
                {
                   await response.Content.ReadAsByteArrayAsync();// Drain response content to free connections.
                }
            }
            return response;
        }
}
```

以下代码演示如何设置 `GraphServcieClient` 类以使用日志记录处理程序：

```
IPublicClientApplication publicClientApplication = PublicClientApplicationBuilder
            .Create(ClientId)
            .WithTenantId(TenantId)
            // Enable MSAL logging
            .WithLogging(MSALlogger, Microsoft.Identity.Client.LogLevel.Verbose, true)
            .WithRedirectUri("http://localhost")
            .Build();

        InteractiveAuthenticationProvider authProvider = new InteractiveAuthenticationProvider(publicClientApplication, Scopes);

        // get the default list of handlers and add the logging handler to the list
        var handlers = GraphClientFactory.CreateDefaultHandlers(authProvider);

        // Remove Compression handler
        var compressionHandler =
            handlers.Where(h => h is CompressionHandler).FirstOrDefault();
        handlers.Remove(compressionHandler);

        // Add SeriLog logger
        handlers.Add(new SeriLoggingHandler());

        InitializeBlobStorageForMSAL().Wait();

        var httpClient = GraphClientFactory.Create(handlers);
        GraphServiceClient graphClient = new GraphServiceClient(httpClient);
```

谨慎

此示例记录敏感信息，包括个人身份信息（PII）和访问令牌。 共享调试日志时要谨慎。

## 检查 MSAL.NET 和 Microsoft Graph 日志

运行示例应用程序后，Microsoft Graph 请求和响应应显示在：

- 控制台窗口。
- 文件中配置的 `appsettings.json` 目录位置。 日志文件名称包括日期，如下所示：

  ![显示本地日志的屏幕截图](media/enable-logging-for-msal-and-microsoft-graph/local-microsoft-graph-logs.png)

对于 Azure Blob 存储日志记录，日志位于 `msallogs` 和 `msgraphlogs` 容器中。

![显示 Azure Blob 存储日志的屏幕截图](media/enable-logging-for-msal-and-microsoft-graph/azure-blob-storage-logs.png)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/enable-logging-for-msal-microsoft-graph)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
