# Internet Explorer 中 MSAL.Net XBAP 应用程序中出现“Cookie 已禁用”错误

## 概要

本文介绍使用 Microsoft Internet Explorer 中的 XAML 浏览器应用程序（XBAP）执行Microsoft Entra ID 登录时返回脚本错误的问题。

## 症状

你会收到脚本错误警告和错误消息，指出 **登录到 Microsoft Entra ID 时禁用** cookie。 在 Internet Explorer 的 XAML 浏览器应用程序（XBAP）中运行类似于以下内容 Microsoft的 .NET 身份验证库（MSAL.NET）代码时，会出现此问题：

```
string tenantId = "<Tenant ID>";
string clientId = "<Application ID>";
string[] Scopes = new string[] { "User.Read" };
string errorMessage = string.Empty;
try
  {
  using (HttpClient httpClient = new HttpClient())
  {
     IPublicClientApplication publicClientApp = PublicClientApplicationBuilder.Create(clientId)
       .WithDefaultRedirectUri()
       .WithAuthority(AzureCloudInstance.AzurePublic, AadAuthorityAudience.AzureAdMyOrg)
       .WithTenantId(tenantId)
       .Build();
        AuthenticationResult authenticationResult = null;
        var t = Task.Run(async () =>
          {
              try
              {
                 authenticationResult = await publicClientApp.AcquireTokenInteractive(Scopes)
                            .WithAccount(null)
                            .WithPrompt(Prompt.ForceLogin)
                            .ExecuteAsync();
                    }
                    catch (Exception ex)
                    {
                        errorMessage = "Error while getting token: " + ex.ToString();
                    }
                });
                t.Wait();

                if (authenticationResult != null)
                {
                    return authenticationResult.AccessToken;
                }
                else
                {
                    return errorMessage;
                }
            }
        }
        catch (Exception ex)
        {
            return ex.Message;
        }
```

## 原因

尽管 XBAP 应用程序在 Internet Explorer 中运行，但它们在自己的进程空间中运行： **PresentationHost.exe**。 此过程是一个高度安全的容器。 XBAP 应用程序使用 WebBrowser 控件托管 Microsoft Entra ID 登录页。 为了最大程度地降低浏览器界面的安全风险，此容器已配置为使用包括阻止 Cookie 的安全限制。 但是，Microsoft Entra ID 登录过程取决于 Cookie。 此冲突会导致脚本错误。

## 解决方案

配置 MSAL.Net 以使用 [系统浏览器](/zh-cn/azure/active-directory/develop/msal-net-web-browsers#system-browser-experience-on-net) - Microsoft Edge 打开 Entra ID 登录页。 然后，按照以下步骤进行所需的更新：

1. 在Azure 门户中，在应用注册**页中找到**你的应用。 在移动和桌面应用程序`http://localhost`注册为重定向 URL。

   [![显示注册为重定向 URL 的 localhost 地址的屏幕截图](media/script-errors-running-msal-net-xbap-app/add-uri.png)](media/script-errors-running-msal-net-xbap-app/add-uri.png#lightbox)
2. 对代码进行以下更改：

   ```
   try
   {
       using (HttpClient httpClient = new HttpClient())
       {
           IPublicClientApplication publicClientApp = PublicClientApplicationBuilder.Create(clientId)
                       .WithRedirectUri("http://localhost")
                       .WithAuthority(AzureCloudInstance.AzurePublic, AadAuthorityAudience.AzureAdMyOrg)
                       .WithTenantId(tenantId)
                       .Build();
           AuthenticationResult authenticationResult = null;

           var t = Task.Run(async () =>
           {
               try
               {
                   authenticationResult = await publicClientApp.AcquireTokenInteractive(Scopes)
                       .WithAccount(null)
                       .WithPrompt(Prompt.ForceLogin)
                       .WithUseEmbeddedWebView(false)
                       .ExecuteAsync();
               }
               catch (Exception ex)
               {
                   errorMessage = "Error while getting token: " + ex.ToString();
               }
           });
   ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/script-errors-running-msal-net-xbap-app)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
