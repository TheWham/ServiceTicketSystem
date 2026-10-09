# 调用 /me 端点时，出现 NoPermissionsInAccessToken 错误

本文讨论在 Microsoft Graph 中调用`NoPermissionsInAccessToken`终结点时收到`/me`错误消息的问题。 本文还介绍了为何无法使用通过客户端凭据授权流程获取的令牌来调用 `/me` 终结点。

## 症状

尝试从基于 Microsoft Entra ID 的应用程序中调用使用客户端凭据授予流的`/me`终结点时，会收到以下错误消息：

```
{
"error": {
"code": "NoPermissionsInAccessToken",
"message": "The token contains no permissions, or permissions can not be understood.",
"innerError": {
"oAuthEventOperationId": "48f66de9-xxx-xxxx1-xxxx-399ea6608ec0",
"oAuthEventcV": "MkVd0xxxxxvjGFVJkoA.1",
"errorUrl": "https://aka.ms/autherrors#error-InvalidGrant",
"requestId": "80f8a0e9-xxxx-xxxx-xxxx-88e5d4bb5bb2",
"date": "2021-07-30T04:04:38"
}
}
}
```

## 原因

该 `/me` 终结点旨在使登录用户能够检索其自己的信息。 若要调用 `/me` 终结点，必须提供一些用户上下文，因为终结点使用委派的权限。 也就是说，使用客户端凭据授予流生成的令牌无法使用 `/me` 终结点，因为缺少用户上下文信息。

使用客户端凭据授予流获取的令牌表示应用程序标识，而不是用户标识。 这些令牌包含用于应用程序权限的 **角色** 声明，而不是用于委托权限的 scp（作用域）声明。 缺少用户上下文使得终结点无法 `/me` 确定与请求关联的用户。

### 示例令牌

**具有用户上下文的令牌（使用用户登录的委托流）**

该令牌通过用户登录的委托流进行授予。 它包含特定于用户的信息和一个包含当前用户权限的声明。

[![显示委托令牌示例的屏幕截图。](media/error-call-me-endpoint-microsoft-graph/token-sign-in-user-context.png)](media/error-call-me-endpoint-microsoft-graph/token-sign-in-user-context.png#lightbox)

**具有应用程序标识的令牌（client\_credentials授权流）**

此令牌是使用客户端凭据授予流生成的。 它不包含特定于用户的信息。 而是包含 `roles` 应用程序权限的声明。

[![显示应用程序令牌示例的屏幕截图。](media/error-call-me-endpoint-microsoft-graph/token-application-context.png)](media/error-call-me-endpoint-microsoft-graph/token-application-context.png#lightbox)

## 解决方案

在应用程序中使用客户端凭据授予流时，必须使用 `/users` 终结点而不是 `/me` 终结点。 可以通过 `/users` 终结点使用应用程序令牌来检索用户特定的信息。

例如，如果要调用 `GET https://graph.microsoft.com/v1.0/me/memberOf` 以生成用户所属的组列表，请使用以下方法：

1. 使用客户端凭据授予流获取应用程序令牌。
2. 确保应用程序具有查询用户信息的 **User.Read.All** 权限。
3. 使用 **用户** 终结点查询特定用户详细信息。 将 {upn} 替换为用户的用户主体名称（UPN）或用户对象 ID。

   ```
   GET https://graph.microsoft.com/v1.0/users/{upn or userID}/memberOf
   ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/error-call-me-endpoint-microsoft-graph)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
