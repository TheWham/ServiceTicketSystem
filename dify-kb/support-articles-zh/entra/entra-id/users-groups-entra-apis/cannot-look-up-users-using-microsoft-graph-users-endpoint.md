# 使用 Microsoft Graph /users 终结点查找用户时，会收到 HTTP 401 响应。

可以使用 Microsoft Graph 终结点以编程方式与租户数据交互。 常见场景是使用 Microsoft Graph `/users` 端点来查找租户中的用户。 在这种情况下，如果在访问令牌中使用委派权限，则需要 `User.Read.All` 这个权限。 有一些方法可以阻止你查找其他用户，例如使用可控制Microsoft Entra 授权设置的 [authorizationPolicy](/zh-cn/graph/api/resources/authorizationpolicy) 对象，除非你是租户管理员。

本文提供了一个解决方案，说明在租户策略配置限制对其他用户的访问后，无法使用 Microsoft Graph `/users` 终结点查找其他用户的问题。

## 症状

在租户中启用对象 `authorizationPolicy` 以防止用户查找作后，新应用程序在执行此作时会收到 401 HTTP 响应。 即使在应用注册期间同意适当的权限并且访问令牌具有适当的权限，也会出现此问题。

## 原因

在`allowedToReadOtherUser`中，`authorizationPolicy`属性被设置为`false`。 此设置可防止默认用户角色读取其他用户。 可以通过 `GET` 请求检查其值。

`GET https://graph.microsoft.com/v1.0/policies/authorizationPolicy`

## 解决方案

若要解决此问题，请将属性的值 `allowedToReadOtherUser` 设置为 `true` 通过 `PATCH` 请求，如下所示：

```
PATCH https://graph.microsoft.com/v1.0/policies/authorizationPolicy
{
    "defaultUserRolePermissions": {
    "allowedToReadOtherUsers": true
    }
}
```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/cannot-look-up-users-using-microsoft-graph-users-endpoint)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
