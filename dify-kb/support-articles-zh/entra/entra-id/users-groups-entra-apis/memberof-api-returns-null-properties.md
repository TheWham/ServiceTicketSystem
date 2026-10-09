# Microsoft Graph API memberOf 返回某些属性的 null 值

本文提供了解决方案，针对调用 Microsoft 图形 API `null`时某些属性被标示为`memberOf`的问题。

## 症状

调用以下 API 之一时，可以返回用户是直接成员的组和目录角色列表时，可以在 `null` JSON 响应中看到除对象类型和 ID 以外的所有属性的值：

```
GET https://graph.microsoft.com/v1.0/me/memberOf
```

```
GET https://graph.microsoft.com/v1.0/users/{id | userPrincipalName}/memberOf
```

下面是一个示例 JSON 响应：

```
{
    "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#directoryObjects",
    "value": [
        {
            "@odata.type": "#microsoft.graph.group",
            "id": "00000003-0000-0000-c000-000000000000",
            "deletedDateTime": null,
            "classification": null,
            "createdDateTime": null,
            "creationOptions": [],
            "description": null,
            "displayName": null,
            "expirationDateTime": null,
            "groupTypes": [],
            "isAssignableToRole": null,
            "mail": null,
            "mailEnabled": null,
            "mailNickname": null,
            "membershipRule": null,
            "membershipRuleProcessingState": null
        }
    ]
}
```

## 原因

当应用程序查询返回 `directoryObject` 类型集合的成员身份时，如果它没有读取资源类型的权限，则返回该类型的成员信息有限。 例如，只能返回对象类型和 ID，其他属性将指示为 null。 为应用程序有权读取的对象类型返回完整信息。

有关详细信息，请参阅 [列出用户直接成员身份](/zh-cn/graph/api/user-list-memberof) 和 [为不可访问的成员对象返回的有限信息](/zh-cn/graph/permissions-overview#limited-information-returned-for-inaccessible-member-objects)。

## 解决方案

若要获取完整信息，请为您的应用程序至少配置 `Directory.Read.All` 权限。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/memberof-api-returns-null-properties)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
