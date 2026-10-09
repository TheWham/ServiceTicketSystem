# 调用 Microsoft Graph 安全 API 时出现 HTTP 403 授权错误

本文提供了调用 Microsoft 图形安全 API 时发生的 HTTP 403 错误的解决方案。

## 症状

使用 Microsoft Graph 安全性 API 调用终结点（例如 `https://graph.microsoft.com/v1.0/security/alert` 和 `https://graph.microsoft.com/beta/security/secoreScores`）时，可能会收到 403 错误，并显示以下消息：

> 身份验证令牌不包含有效权限，或者用户没有有效角色

## 原因

此错误是由于以下原因之一导致的：

- Microsoft Graph 权限不足，导致访问令牌无法满足安全终结点的需要。
- 获取访问令牌的身份验证用户没有委托权限类型的令牌所需的 Microsoft Entra 管理员角色。

## 解决方案 1：使用有效的Microsoft图形权限

有两种类型的令牌：应用程序和委托的权限令牌。 有关详细信息，请参阅 [Microsoft标识平台中访问令牌的应用程序和委派权限](../app-integration/application-delegated-permission-access-tokens-identity-platform)。

对于委派的权限令牌，Microsoft Graph 权限位于 `scp` 声明中。 对于应用程序权限令牌，权限位于 `roles` 声明中。 若要获取所需的Microsoft Graph 权限，可以参考下表，该表也列在 [授权和 Microsoft Graph 安全 API](/zh-cn/graph/security-authorization#register-an-application-with-the-microsoft-identity-platform-endpoint) 中：

| 许可 | 实体 | 支持的请求 |
| --- | --- | --- |
| 安全操作.读取.全部 | • [securityActions](/zh-cn/graph/api/resources/securityaction) （预览版） | 获取 |
| SecurityActions.ReadWrite.All | • [securityActions](/zh-cn/graph/api/resources/securityaction) （预览版） | GET、POST |
| 安全事件.读取.全部 | • [警报](/zh-cn/graph/api/resources/alert)  • [secureScores](/zh-cn/graph/api/resources/securescore)  • [secureScoreControlProfiles](/zh-cn/graph/api/resources/securescorecontrolprofiles) | 获取 |
| SecurityEvents.ReadWrite.All | • [警报](/zh-cn/graph/api/resources/alert)  • [secureScores](/zh-cn/graph/api/resources/securescore)  • [secureScoreControlProfiles](/zh-cn/graph/api/resources/securescorecontrolprofiles) | GET、POST、PATCH |
| 威胁指示器.读取写入.所属者 | • [tiIndicator](/zh-cn/graph/api/resources/tiindicator) （预览版） | GET、POST、PATCH、DELETE |

有关详细信息，请参阅 [使用 Microsoft Graph 安全 API](/zh-cn/graph/api/resources/security-api-overview) 和 [Microsoft Graph 权限参考](/zh-cn/graph/permissions-reference)。

## 解决方案 2：使用有效的Microsoft Entra 管理员角色

对于委派的权限令牌，身份验证用户需要具有以下管理员角色之一：

| Microsoft Entra 角色 | 角色模板 ID |
| --- | --- |
| 安全读取器 | 5d6b6bb7-de71-4623-b4af-96380a352509 |
| 安全管理员 | 194ae4cb-b126-40b2-bd5b-6091b380977d |
| 全局管理员 | 62e90394-69f5-4237-9190-012177145e10 |

有关详细信息，请参阅 [Microsoft Entra 内置角色](/zh-cn/entra/identity/role-based-access-control/permissions-reference) 和 [授权以及Microsoft图形安全 API](/zh-cn/graph/security-authorization)。

令牌 `wids` 中的声明包含 Microsoft Entra 角色。 它可用于确定用户是否具有足够的权限。

```
"ver": "1.0"
"wids": [
   "62e90394-69f5-4237-9190-012177145e10",
   "b79fbf4d-3ef9-4689-8143-76b194e85509"
],
"xms_st":{
  "sub": "<sub>"
}
```

注释

如果令牌是通过 [隐式授权流](/zh-cn/entra/identity-platform/v2-oauth2-implicit-grant-flow)获取的，则 `wids` 声明可能不存在。 有关详细信息，请参阅 [Microsoft 标识平台中的访问令牌](/zh-cn/entra/identity-platform/access-tokens)。 在这种情况下，请使用其他 OAuth 2 授权流（例如 [授权代码流](/zh-cn/entra/identity-platform/v2-oauth2-auth-code-flow)）来获取访问令牌。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/403-error-when-calling-microsoft-graph-security-api)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
