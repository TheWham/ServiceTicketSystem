# 错误“无法建立调用应用程序的标识”

本文提供了使用 Microsoft Graph 时错误消息“无法建立调用应用程序的标识”的解决方案。

## 症状

使用 Microsoft Graph 或依赖于它的某些服务时，遇到以下错误消息：

> 无法建立调用应用程序的身份

## 原因

此错误是因为访问令牌中缺少 `oid` 和 `sub` 声明。 根本原因是租户中不存在服务主体，或者租户不知道应用程序。

## 解决方案

若要解决此错误，请将服务主体添加到租户并同意应用程序所需的权限。

可以 [生成管理员同意 URL](/zh-cn/entra/identity/enterprise-apps/grant-admin-consent#construct-the-url-for-granting-tenant-wide-admin-consent) ，如下所示：

`https://login.microsoftonline.com/{organization}/adminconsent?client_id={client-id}`

然后，使用尝试访问资源的租户的全局管理员帐户登录。

注释

- 替换为 `{organization}` 租户 ID，例如 aaaaaaaa-bbbb-cccc-1111-222222222。
- 将 `{client-id}` 替换为应用程序 ID，例如 dddddddddddd-eeee-ffff-3333-44444444。

## 参考

- [了解 Microsoft Entra 应用程序同意体验](/zh-cn/entra/identity-platform/application-consent-experience)
- [Microsoft标识平台](/zh-cn/entra/identity-platform/permissions-consent-overview) 中的权限和同意概述
- [停用服务 Principal-Less 身份验证](/zh-cn/entra/identity-platform/retire-service-principal-less-authentication)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/identity-of-calling-application-not-established)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
