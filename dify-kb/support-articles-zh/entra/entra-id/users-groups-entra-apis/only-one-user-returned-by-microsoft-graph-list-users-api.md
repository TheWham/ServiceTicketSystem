# Microsoft Graph 列表用户 API 仅返回目录中的一个用户

本文提供了一个解决方案，用于解决Microsoft Graph REST API [列表用户](/zh-cn/graph/api/user-list) 时在目录中仅返回一个用户的问题。

## 症状

请考虑以下方案：

- 通过单击右上角的个人资料图标，登录到 [Microsoft Graph 资源管理器](https://developer.microsoft.com/en-us/graph/graph-explorer)。

  [![显示Microsoft Graph 资源管理器中的登录按钮的屏幕截图。](media/only-one-user-returned-by-microsoft-graph-list-users-api/microsoft-graph-explorer-sign-in.png)](media/only-one-user-returned-by-microsoft-graph-list-users-api/microsoft-graph-explorer-sign-in.png#lightbox)
- 登录后，尝试运行此查询 `GET https://graph.microsoft.com/v1.0/users` 以检索目录中的所有用户。

在这种情况下，仅返回一个用户。 预期输出是目录中多个用户的列表。

[![显示查询结果的屏幕截图。](media/only-one-user-returned-by-microsoft-graph-list-users-api/list-users-query-result.png)](media/only-one-user-returned-by-microsoft-graph-list-users-api/list-users-query-result.png#lightbox)

## 原因

出现此问题的原因是使用个人Microsoft帐户（MSA）登录，如前面的屏幕截图所示。 个人帐户无权访问 Microsoft Entra ID 中的组织目录数据。 因此，查询仅返回与个人帐户关联的用户。

## 解决方案

若要检索目录中的所有用户，必须使用组织Microsoft Entra 帐户（例如 `userPrincipalName = name@tenant.onmicrosoft.com`）登录到 Microsoft Graph 资源管理器。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/only-one-user-returned-by-microsoft-graph-list-users-api)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
