# Microsoft 标识平台中访问令牌的应用程序和委派权限

## 概要

本文介绍应用程序与Microsoft 标识平台中访问令牌的委托权限之间的差异，以帮助诊断应用程序调用 Web API 时出现的问题。

## 概述

如Microsoft 标识平台[和](/zh-cn/entra/identity-platform/developer-glossary)[术语表中的权限和同意概述中所述](/zh-cn/entra/identity-platform/permissions-consent-overview)：Microsoft 标识平台，访问令牌有两种类型的权限：委派的权限和应用程序权限。 委派的权限授予已登录用户，而应用程序权限则直接授予应用程序。 主要区别在于，委派的权限需要用户登录，而应用程序权限则不需要;相反，应用程序使用自己的应用程序标识（客户端 ID 和机密/断言）向 Microsoft Entra ID 进行身份验证。

无论权限类型如何，都必须**在“Microsoft Entra [应用注册](/zh-cn/entra/identity-platform/quickstart-configure-app-access-web-apis#add-permissions-to-access-your-web-api)”页上配置 API 权限**：

- 如果应用程序不需要任何用户登录，请选择 **“应用程序”权限** 。
- 如果应用程序要求用户登录，以便可以针对该登录颁发访问令牌，请选择 **“委派权限** ”。

备注

选择 **应用程序权限**时，必须授予管理员同意才能正常运行的权限。

## 从 OAuth2 身份验证流颁发的权限类型令牌

Microsoft Entra ID 支持各种 OAuth2 身份验证流。 应用程序使用的身份验证流类型会导致访问令牌中的特定权限类型。

只能从 [客户端凭据授予流](/zh-cn/entra/identity-platform/v2-oauth2-client-creds-grant-flow)获取应用程序权限令牌。

只能从以获取委派的权限令牌：

- [隐式授权流](/zh-cn/azure/active-directory/develop/v2-oauth2-implicit-grant-flow)
- [授权代码授予流](/zh-cn/azure/active-directory/develop/v2-oauth2-auth-code-flow)
- [代理流](/zh-cn/azure/active-directory/develop/v2-oauth2-on-behalf-of-flow)
- [设备授权授权流](/zh-cn/azure/active-directory/develop/v2-oauth2-device-code)
- [资源所有者密码凭据授予流](/zh-cn/entra/identity-platform/v2-oauth-ropc)

## 标识访问令牌的权限类型

若要确定访问令牌是委托令牌还是应用程序权限令牌，请使用 jwt.ms [等](https://jwt.ms/)工具来检查令牌声明。

对于应用程序权限令牌，权限位于声明中 `roles` ：

```
"oid": "<oid>"
"roles": [
    "User.Read.All"
],
"sub": "<sub>"
```

备注

应用程序 `scp` 权限令牌中缺少声明。

对于委派的权限令牌，权限位于 `scp` 声明中：

```
"scp": "Directory.Read.All User.Read",
"sub": "<sub>",
```

备注

声明 `roles` 可能仍显示在委派的权限令牌中，但它列出了分配给 API 应用中用户的角色。

## 标识 API 支持的权限类型

了解 API 支持的权限类型至关重要。 当应用程序调用不同 API（例如，Microsoft Graph 和 Power BI）时，会出现许多错误，例如 400、401、403 和 500，其权限类型令牌不正确。 对于 API，不同的 REST 终结点可能需要不同的权限类型。 可以参考 API 终结点文档来检查支持的权限类型。 还需要评估应用程序中使用的身份验证流是否生成所需的权限令牌。

### 示例方案

Power BI API：虽然 Power BI 同时支持委派权限和应用程序权限，但某些任务（如查看报表（需要 **Report.Read.All** 权限）只能使用委托令牌执行。 在 **“应用注册** ”页上， **应用程序权限仅支持两个权限** ： **Tenant.Read.All** 和 **Tenant.ReadWrite.All。**

![显示 Power BI API 的应用程序权限的屏幕截图。](media/application-delegated-permission-access-tokens-identity-platform/application-permissions-power-bi-api.png)

相比之下， **委派的权限** 提供更丰富的功能集：

![显示 Power BI API 的委派权限的屏幕截图。](media/application-delegated-permission-access-tokens-identity-platform/delegated-permissions-power-bi-api.png)

## 排查调用 Microsoft Graph REST 终结点时出现的问题

当用户的应用程序调用 Microsoft Graph REST 终结点时，用户通常会遇到问题。 请求在 Microsoft Graph 资源管理器中成功工作，但在其应用程序中失败。 若要排查这些问题，请检查以下事项：

- 检查访问令牌具有的权限类型。 Microsoft Graph 资源管理器始终使用委派的权限令牌。
- 确保使用相同的用户帐户登录到 Microsoft Graph Explorer 和应用程序。
- 验证终结点是否支持委派的权限、应用程序权限或两者。
- 验证访问令牌是否具有调用终结点的正确权限。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/application-delegated-permission-access-tokens-identity-platform)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
