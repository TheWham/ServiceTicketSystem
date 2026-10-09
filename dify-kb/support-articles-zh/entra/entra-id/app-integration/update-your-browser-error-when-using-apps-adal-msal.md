# MSAL 应用中出现“浏览器不受支持或 up-to-date”错误

## 概要

本文讨论如何解决基于 Microsoft 身份验证库 (MSAL) 的应用程序中出现的“Your browser is not supported or up-to-date”错误。

## 症状

打开与 MSAL 集成的应用并尝试注册Microsoft Entra ID 多重身份验证（MFA），将收到以下错误消息：

> 浏览器不受支持或最新。 请尝试更新它，或者下载并安装最新版本的 Microsoft Edge。
> 还可以尝试从其他设备访问 <https://aka.ms/mysecurityinfo> 。

## 原因

如果 MSAL 应用使用过时的 Web 浏览器控件（如 WebView1），则会出现此问题。 这些较旧的控件不支持Microsoft Entra ID MFA 注册或自助密码重置向导。

## 决议

### 对于用户

若要解决此问题，请使用受支持的浏览器注册 Microsoft Entra ID 多重身份验证（MFA），然后再使用应用：

1. 在 Microsoft Edge 或其他受支持的浏览器中打开 [“我的应用](https://myapps.microsoft.com) ”。
2. 完成 MFA 注册过程。
3. 成功注册后，打开应用。

## 面向开发人员

若要解决此问题，请在应用中使用 [Web 帐户管理器](/zh-cn/entra/identity-platform/scenario-desktop-acquire-token-wam) 启用代理身份验证。

以下示例代码创建一个客户端以使用 Broker 身份验证：

```
var pca = PublicClientApplicationBuilder.Create("client_id").WithBroker(new BrokerOptions(BrokerOptions.OperatingSystems.Windows))
```

如果 Web 帐户管理器不可用（例如在 Windows Server 2012 上），请考虑使用 [默认系统浏览器进行身份验证](/zh-cn/entra/msal/dotnet/acquiring-tokens/using-web-browsers#how-to-use-the-default-system-browser)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/update-your-browser-error-when-using-apps-adal-msal)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
