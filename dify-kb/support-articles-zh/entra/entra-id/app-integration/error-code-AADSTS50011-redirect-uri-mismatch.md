# OpenID 身份验证AADSTS50011错误：请求中指定的重定向 URI 不匹配

## 概要

本文介绍 `AADSTS50011` 尝试使用基于 OpenID Connect（OIDC）的身份验证通过 Microsoft Entra ID 登录时返回错误消息的问题。

## 现象

尝试使用带有 Microsoft Entra ID 的 OIDC 或 OAuth2 身份验证协议登录到应用程序时，会收到以下错误消息：

> 错误AADSTS50011 - 请求中指定的重定向 URI <重定向 URI 与为应用程序 >AppGUID< 配置的重定向 URI> 不匹配。 确保请求中发送的重定向 URI 与在 Azure 门户中添加到应用程序的重定向 URI 匹配。 导航至 <https://aka.ms/redirectUriMismatchError>，了解有关如何解决此问题的详细信息。

## 原因

如果应用程序（代码）中配置的重定向 URI（回复 URL）与 Microsoft Entra 应用注册不匹配，则会发生此错误。

当用户访问应用程序进行身份验证时，应用程序会使用预定义的重定向 URI 将用户重定向到 Microsoft Entra ID。 成功授权用户后，Microsoft Entra ID 验证以下值：

- 从应用程序发送的重定向 URI
- Microsoft Entra ID 中已注册应用程序中的重定向 URI 值

如果应用程序发送的重定向 URI 与 Microsoft Entra ID 中的任何重定向 URI 不匹配，将返回错误AADSTS50011。 如果值匹配，Microsoft Entra ID 会将用户发送到重定向 URI。

## 解决方法

若要解决此问题，请按照以下步骤在 Microsoft Entra 应用注册中添加重定向 URI。

1. 从错误消息中复制应用程序 ID。 这是已在 Microsoft Entra ID 中注册的应用程序的 ID。
   ![有关AADSTS50011错误消息中的应用程序 ID 的屏幕截图](media/error-code-aadsts50011-redirect-uri-mismatch/aadsts50011-error-appid.png)
2. 转到 [Azure 门户](https://portal.azure.com)。 请确保使用有权更新 Microsoft Entra 应用程序注册的帐户登录到门户。
3. 导航到**Microsoft Entra ID，选择**应用注册**，使用应用程序 ID** 找到应用程序注册，然后打开应用注册页。

   还可以使用以下链接直接打开页面：

   - 如果此应用归组织所有（Microsoft Entra 租户），请使用 `https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/Authentication/appId/<AppGUID>`。
   - 如果此应用由个人 Microsoft (MSA) 帐户拥有，请使用 `https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/Authentication/appId/<AppGUID>/isMSAApp/true`。
4. 在应用注册页上，选择“ **身份验证**”。 在 **“平台配置** ”部分中，选择“ **添加 URI** ”以添加错误消息中显示的重定向 URI，以Microsoft Entra ID。

   ![有关AADSTS50011错误消息中的重定向 URI 的屏幕截图](media/error-code-aadsts50011-redirect-uri-mismatch/aadsts50011-error-redirecturi.png)
5. 保存更改并等待三到五分钟，使更改生效，然后再次发送登录请求。 现在你应该能够登录该应用程序。 如果未看到Microsoft Entra 登录页，请尝试从浏览器清除密码缓存或使用 InPrivate 浏览。

注意

如果从应用程序发送的重定向 URI 不是所需的 URI，则应更新应用程序代码或配置。

以下视频演示如何修复Microsoft Entra ID 中的重定向 URI 不匹配错误：

## 详细信息

有关 Active Directory 身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/azure/active-directory/develop/reference-aadsts-error-codes)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-AADSTS50011-redirect-uri-mismatch)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
