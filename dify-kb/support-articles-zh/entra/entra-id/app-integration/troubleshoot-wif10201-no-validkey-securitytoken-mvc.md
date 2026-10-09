# WIF10201：在 ASP.NET 应用程序中找不到 securityToken 错误的有效密钥映射

## 概要

本文提供有关排查 ASP.NET MVC 应用程序中发生的身份验证问题的指南，该应用程序使用 [WS 联合](https://github.com/Azure-Samples/active-directory-dotnet-webapp-wsfederation) OWIN 中间件和 [Windows Identity Foundation](../../../windows-server/user-profiles-and-logon/windows-identity-foundation) （WIF） 进行身份验证以Microsoft Entra ID。

## 症状

以前工作的 ASP.NET MVC 应用程序生成以下错误消息，尽管未对应用程序进行更改：

```
Error Details:
Server Error in '/' Application.
WIF10201: No valid key mapping found for securityToken: 'System.IdentityModel.Tokens.X509SecurityToken' and issuer: 'https://sts.windows.net/<Directory ID>/'.

Description: An unhandled exception occurred during the execution of the current web request. Please review the stack trace for more information about the error and where it originated in the code.

Exception Details: System.IdentityModel.Tokens.SecurityTokenValidationException: WIF10201: No valid key mapping found for securityToken: 'System.IdentityModel.Tokens.X509SecurityToken' and issuer: 'https://sts.windows.net/<Directory ID>/'.
```

## 原因

若要在成功登录后验证 Entra ID 返回的令牌的签名，WIF 使用 Web.config **文件中的证书指纹**，如以下示例所示：

```
<issuerNameRegistry type="System.IdentityModel.Tokens.ValidatingIssuerNameRegistry, 
System.IdentityModel.Tokens.ValidatingIssuerNameRegistry">
<authority name="https://sts.windows.net/<Directory ID>/">
    <keys>
    <add thumbprint="C142E..." />
    <add thumbprint="8BA94..." />
    <add thumbprint="D92E1..." />
    </keys>
    <validIssuers>
    <add name="https://sts.windows.net/<Directory ID>/" />
    </validIssuers>
</authority>
</issuerNameRegistry>
```

如果这些证书指纹都与 Entra ID 用来对令牌进行签名的证书指纹匹配，则会发生“WIF10201”错误。

Entra ID 使用 [签名密钥滚动更新机制](/zh-cn/entra/identity-platform/signing-key-rollover) 来更新用于定期对身份验证令牌进行签名的证书。 此密钥滚动更新会导致 Web.config **文件中配置**的初始证书指纹变为无效。

## 解决方案

可以手动更新 Web.config **文件中的**证书指纹，也可以通过代码自动执行该过程。 有关详细信息，请参阅 [密钥元数据缓存和验证](/zh-cn/entra/identity-platform/signing-key-rollover#best-practices-for-keys-metadata-caching-and-validation)的最佳做法。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/troubleshoot-wif10201-no-validkey-securitytoken-mvc)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
