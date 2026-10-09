# 排查使用 Microsoft Graph API 将用户添加到组时出现的 403 错误

本文提供了对尝试使用 Microsoft Graph API 将用户添加到组时发生的“403 Authorization\_RequestDenied”错误的故障排除指南。

## 症状

当您尝试使用 Microsoft Graph API 将用户添加到组时，您会收到以下“403”错误消息：

```
{
"error": {
"code": "Authorization_RequestDenied",
"message": "Insufficient privileges to complete the operation.",
"innerError": {
"date": "2024-05-07T15:39:39",
"request-id": "aa324f0f-b4a3-4af6-9c4f-996e195xxxx",
"client-request-id": "aa324f0f-b4a3-4af6-9c4f-996e1959074e"
}
}
}
```

## 原因

如果您尝试将用户添加到的组无法由 Microsoft Graph 管理，则会出现此问题。 Microsoft Graph 仅支持 Microsoft 365 组和安全组。

## 解决方案

### 第 1 步：检查组类型

确保 Microsoft Graph 支持您尝试修改的组。

1. 在 Microsoft Graph 中，组类型可以由其 `groupTypes`、 `mailEnabled`和 `securityEnabled` 属性的设置来确定。 使用 [Microsoft Graph 浏览器](https://developer.microsoft.com/graph/graph-explorer) 检查组的属性：

   ```
   https://graph.microsoft.com/v1.0/groups/<Group Object ID>?$select=displayName,groupTypes,mailEnabled,securityEnable
   ```

   示例响应：

   ```
       {
        "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#groups(displayName,groupTypes,mailEnabled,securityEnabled)/$entity",
       "displayName": "Test group A",
       "groupTypes": [],
       "mailEnabled": true,
       "securityEnabled": false
       }
   ```
2. 查看下表以验证 Microsoft Graph API 是否支持该组类型。 在示例响应中，“测试组 A”是 Microsoft Graph 不支持的分发组。 有关详细信息，请参阅 [在 Microsoft Graph 中使用组](/zh-cn/graph/api/resources/groups-overview)。

   | 类型 | 组类型 | mail已启用 | securityEnabled 已启用 | 可以使用 Microsoft Graph API 进行管理 |
   | --- | --- | --- | --- | --- |
   | [Microsoft 365 组](/zh-cn/graph/api/resources/groups-overview#microsoft-365-groups) | `["Unified"]` | `true` | `true` 或 `false` | 是的 |
   | [安全组](/zh-cn/graph/api/resources/groups-overview#security-groups-and-mail-enabled-security-groups) | `[]` | `false` | `true` | 是的 |
   | [启用邮件的安全组](/zh-cn/graph/api/resources/groups-overview#security-groups-and-mail-enabled-security-groups) | `[]` | `true` | `true` | 不;通过 Microsoft Graph 只读 |
   | 通讯组 | `[]` | `true` | `false` | 不;通过 Microsoft Graph 只读 |

   注释

   - 组类型在创建后无法更改。 有关更多信息，请参阅 [编辑组设置](/zh-cn/entra/fundamentals/how-to-manage-groups#edit-group-settings)。
   - 动态组的成员身份（**groupTypes** 包含“DynamicMembership”）无法通过 Microsoft Graph 进行管理。

### 第 2 步：验证所需的权限

不同的组成员类型需要特定的权限。 对于用户类型的成员资格，请确保执行操作的应用程序或帐户具有`GroupMember.ReadWrite.All`权限。

有关详细的权限要求，请参阅 [添加成员文档](/zh-cn/graph/api/group-post-members)。

### 步骤 3：检查组是否为可分配角色的组

1. 可分配角色的组需要额外的权限才能管理其成员。 可以使用 Azure 门户或 Microsoft Graph Explorer 验证组是否可分配角色：

   Azure 门户

   1. 在 [Azure 门户中](https://portal.azure.com)，转到 **Microsoft Entra ID**，选择 **“组”**，然后选择 **“所有组**”。
   2. 找到目标组，选择 Properties （ **属性**），然后检查 **是否可以将 Microsoft Entra 角色分配给该组** 是否设置为 **Yes（是**）。

   **Microsoft Graph 浏览器**

   要检查 `isAssignableToRoles` 该值，请运行以下请求：

   ```
   GET https://graph.microsoft.com/v1.0/groups/<group object="" id="">?$select=displayName,groupTypes,mailEnabled,securityEnabled,isAssignableToRole
   ```

   示例响应：

   ```
    {
        "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#groups(displayName,groupTypes,mailEnabled,securityEnabled,isAssignableToRole)/$entity",
       "displayName": "Test group B",
       "groupTypes": [],
       "mailEnabled": false,
       "securityEnabled": true,
       "isAssignableToRole": true
       }
   ```
2. 如果该组可以分配角色，则除`RoleManagement.ReadWrite.Directory`之外，您还需要`GroupMember.ReadWrite.All`权限。 有关更多信息，请参阅 [添加成员文档](/zh-cn/graph/api/group-post-members)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/authorization-requestdenied-403-error-add-user-group)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
