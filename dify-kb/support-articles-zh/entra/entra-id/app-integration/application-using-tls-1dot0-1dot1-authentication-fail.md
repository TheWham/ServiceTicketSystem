# Microsoft使用 TLS 1.0/1.1 的 Entra 应用程序无法进行身份验证

## 概要

本文提供了解决 Microsoft Entra 集成应用程序在早于 Microsoft .NET Framework 4.7 的版本中发生的身份验证错误的方案。

## 症状

使用旧版 .NET Framework 的应用程序可能会遇到以下错误消息之一的身份验证失败：

- > AADSTS1002016：你正在使用已弃用的 TLS 版本 1.0、1.1 和/或 3DES 密码来改善 Azure AD 的安全状况
- > IDX20804：无法从“[PII 已隐藏]”检索文档
- > IDX20803：无法从“[PII 已隐藏]”获取配置
- > IDX10803：无法创建从：“”https://login.microsoftonline.com/{Tenant-ID}/.well-known/openid-configuration 获取配置
- > IDX20807：无法从“System.String”检索文档
- > System.Net.Http.Headers.HttpResponseHeaders RequestMessage {方法： POST， RequestUri： '<request-uri>'， Version： 1.1， Content： System.Net.Http.FormUrlEncodedContent， Headers： { Content-Type： application/x-www-form-urlencoded Content-Length： 970 }} System.Net.Http.HttpRequestMessage StatusCode UpgradeRequired 此服务需要使用 TLS-1.2 协议

## 原因

从 2022 年 1 月 31 日开始，Microsoft对连接到 Microsoft 标识平台上Microsoft Entra 服务的客户端应用程序强制使用 TLS 1.2 协议，以确保符合安全性和行业标准。 有关此更改的详细信息，请参阅如何在您的环境中启用对 Microsoft Entra 的 TLS 1.2 支持，以逐步淘汰 TLS 1.1 和 1.0，并立即行动，通过迁移到 TLS 1.2 来保障您的基础设施安全！

在较旧平台上运行或使用较旧的 .NET Framework 版本的应用程序可能未启用 TLS 1.2。 因此，它们无法检索 OpenID Connect 元数据文档，从而导致身份验证失败。

## 解决方案 1：升级 .NET Framework

将应用程序升级为使用 .NET Framework 4.7 或更高版本，其中默认启用 TLS 1.2。

## 解决方案 2：以编程方式启用 TLS 1.2

如果升级 .NET Framework 不可行，可以通过将以下代码添加到应用程序中 **的 Global.asax.cs** 文件来启用 TLS 1.2：

```
using System.Net;

protected void Application_Start()
{
ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12 | SecurityProtocolType.Ssl3; // only allow TLS 1.2 and SSL 3
// The rest of your startup code goes here
}
```

## 解决方案 3：更改 web.config 以启用 TLS 1.2

如果 .NET Framework 4.7.2 可用，可以通过将以下配置添加到 **web.config** 文件来启用 TLS 1.2：

```
<system.web>
    <httpRuntime targetFramework="4.7.2" />
</system.web>
```

注释

如果使用 .NET Framework 4.7.2 会导致应用发生中断性变更，则此解决方案可能无法正常工作。

## 解决方案 4：在运行 PowerShell 命令之前启用 TLS 1.2

如果在运行 PowerShell 命令 `Connect-MSolService`时遇到AADSTS1002016错误， `Connect-AzureAD`或者 `Connect-MSGraph` （从 Microsoft Intune PowerShell SDK 模块），则在执行命令之前将安全协议设置为 TLS 1.2：

```
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
```

## 参考文献

[使用 .NET Framework 的传输层安全性 （TLS） 最佳做法](/zh-cn/dotnet/framework/network-programming/tls)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/application-using-tls-1dot0-1dot1-authentication-fail)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
