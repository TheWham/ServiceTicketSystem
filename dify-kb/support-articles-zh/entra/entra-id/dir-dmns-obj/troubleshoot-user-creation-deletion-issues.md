# 排查 Microsoft Entra ID 中的用户创建和删除问题

本文 Microsoft概述了可用于：

- 创建一个用户。
- 删除用户。
- 批量创建用户。

## 先决条件

- 以下角色分配之一：

  - [全局管理员](/zh-cn/azure/active-directory/roles/permissions-reference#global-administrator)
  - [用户管理员](/zh-cn/azure/active-directory/roles/permissions-reference#user-administrator)

## 用户创建和删除的方法

Microsoft Entra ID 有许多用于创建和删除用户的方法，例如：

- [Azure 门户](https://portal.azure.com)
- [Microsoft 图形 REST API](/zh-cn/graph/use-the-api)
- [Azure PowerShell](/zh-cn/powershell/azure/what-is-azure-powershell)
- [Azure CLI](/zh-cn/cli/azure/what-is-azure-cli)

这些方法是指直接在 Microsoft Entra ID 中创建的用户。 本文不包括在其他地方创建的用户，然后同步到 Microsoft Entra ID 或企业到企业方案。

## 创建用户

选择一个方法，在 Microsoft Entra ID 中创建用户。

- [Azure 门户](#tabpanel_1_azure-portal)
- [Microsoft Graph](#tabpanel_1_microsoft-graph)
- [Microsoft Graph PowerShell](#tabpanel_1_microsoft-graph-powerShell)
- [Azure CLI](#tabpanel_1_azure-cli)

若要在Azure 门户添加新用户，请执行以下操作：

1. 在[Azure 门户](https://portal.azure.com)中，以全局管理员或用户管理员身份登录。
2. 搜索并选择 **Microsoft Entra ID**。
3. 依次选择“用户”、“新建用户”。
4. 在**“用户**”页上，输入用户**的姓名**、**用户名**、组**、目录角色**和**作业信息**。
5. 复制“密码”框中提供的自动生成的密码。 需将此密码提供给用户，供其在首次登录时使用。
6. 选择**创建**。

有关详细信息，请参阅 [添加或删除用户 - Microsoft Entra ID](/zh-cn/azure/active-directory/fundamentals/add-users-azure-active-directory)。

若要在 Microsoft Graph 中添加用户，请使用 [创建用户 API](/zh-cn/graph/api/user-post-users)：

```
POST https://graph.microsoft.com/v1.0/users 
Content-type: application/json { 
  "accountEnabled": true, 
  "displayName": "<New User>", 
  "mailNickname": "<Newuser>", 
  "userPrincipalName": "<NewUser@contoso.onmicrosoft.com>", 
  "passwordProfile" : { 
    "forceChangePasswordNextSignIn": true, 
    "password": "xWwvJ]6NMw+bWH-d" 
  }
}
```

若要在 Microsoft Graph PowerShell 中添加用户，请运行 [New-MgUser](/zh-cn/powershell/module/microsoft.graph.users/new-mguser?view=graph-powershell-1.0&preserve-view=true) cmdlet。 若要运行此命令，必须至少具有 `User.ReadWrite.All` 权限连接到 Microsoft Graph。

```
$PasswordProfile = @{
  Password = 'xWwvJ]6NMw+bWH-d'
  }
Connect-MgGraph -Scopes "User.ReadWrite.All"
New-MgUser -DisplayName 'Rene Magi' -PasswordProfile $PasswordProfile -AccountEnabled -MailNickName 'ReneMagi' -UserPrincipalName 'ReneMagi@contoso.com'
```

若要在 Azure CLI 中添加用户，请运行 [az ad user create](/zh-cn/cli/azure/ad/user#az-ad-user-create) 命令：

```
az ad user create --display-name "<New User>" \
    --password "xWwvJ]6NMw+bWH-d" \
    --user-principal-name "<NewUser@contoso.onmicrosoft.com>" \
    [--force-change-password-next-login {false, true}] \
    [--immutable-id "<base64-string-representation-of-object-guid>"] \
    [--mail-nickname "<Newuser>"]
```

## 删除用户

选择一种方法以删除Microsoft Entra ID 中的用户。

- [Azure 门户](#tabpanel_2_azure-portal)
- [Microsoft Graph](#tabpanel_2_microsoft-graph)
- [Microsoft Graph PowerShell](#tabpanel_2_microsoft-graph-powerShell)
- [Azure CLI](#tabpanel_2_azure-cli)

删除Azure 门户中的用户：

1. 在[Azure 门户](https://portal.azure.com)中，以全局管理员或用户管理员身份登录。
2. 搜索并选择 **Microsoft Entra ID**。
3. 选择**用户**。
4. 搜索并选择要从 Microsoft Entra 租户中删除的用户（例如 **Mary Parker**）。
5. 选择“删除用户” 。

用户将被删除并且不再显示在“用户 - 所有用户”页上。 可以在“已删除的用户”页面上查看用户，在接下来的 30 天内。 在此期间，还可以还原已删除的用户。 有关还原用户的详细信息，请参阅[使用 Microsoft Entra ID 还原或永久删除最近删除的用户](/zh-cn/azure/active-directory/fundamentals/active-directory-users-restore)。

删除用户后，用户使用的任何许可证都可供其他用户使用。

若要删除 Microsoft Graph 中的用户，请使用 [“删除用户 API](/zh-cn/graph/api/user-delete)：

```
DELETE https://graph.microsoft.com/v1.0/users/{user-id-or-user-principal-name}
```

例如，如果要删除具有主体名称 `NewUser@contoso.onmicrosoft.com`的用户，请使用以下命令：

```
DELETE https://graph.microsoft.com/v1.0/users/NewUser@contoso.onmicrosoft.com
```

若要在 Azure PowerShell 中删除用户，请运行 [Remove-MgUser](/zh-cn/powershell/module/microsoft.graph.users/remove-mguser?view=graph-powershell-1.0&preserve-view=true) cmdlet。 若要运行此命令，必须至少具有 `User.DeleteRestore.All` 权限连接到 Microsoft Graph。

```
Remove-MgUser -UserId '00aa00aa-bb11-cc22-dd33-44ee44ee44ee'
```

若要在 Azure CLI 中删除用户，请运行 [az ad user delete](/zh-cn/cli/azure/ad/user#az-ad-user-delete) 命令：

```
Connect-MgGraph -Scopes "User.DeleteRestore.All"
az ad user delete --id "<NewUser@contoso.onmicrosoft.com>"
```

## 批量创建用户

有关批量创建或删除用户的详细信息，请参阅 [Microsoft Entra ID](/zh-cn/azure/active-directory/enterprise-users/users-bulk-add) 中的批量创建用户。

## 使用服务主体管理用户所需的权限

如果要在 Microsoft Graph 上自动创建和删除 Microsoft Entra 用户，应用程序需要以下权限：

- [User.ReadWrite.All](/zh-cn/graph/permissions-reference#user-permissions)
- [Directory.ReadWrite.All](/zh-cn/graph/permissions-reference#directory-permissions)

有关谁可以管理用户管理的各个方面的详细信息，请参阅 [Microsoft Entra ID 中的任务中的最低特权角色 — 用户](/zh-cn/azure/active-directory/roles/delegate-by-task#users)。

## 错误消息和修正操作

下表包含尝试在 Microsoft Entra ID 中创建或删除用户时的常见错误消息列表，并描述它们的正确修正操作。 错误消息如Microsoft图形 REST API、Azure PowerShell 或 Azure CLI 所示。 类似，但较简短的错误消息显示在Azure 门户中，修正操作是相同的。

| 错误消息 | 目的 |
| --- | --- |
| *已存在属性 userPrincipalName 具有相同值的另一个对象。* | 将用户主体名称 (UPN) 设为唯一。 当管理员尝试使用 Microsoft Entra ID 中的现有用户名创建用户时，会发生此错误。 有关详细信息，请参阅[用户名策略](/zh-cn/azure/active-directory/authentication/concept-sspr-policy#userprincipalname-policies-that-apply-to-all-user-accounts)。 |
| *权限不足，无法完成操作。* | 查找全局管理员或用户管理员以添加或删除用户。 当安全主体尝试创建或删除用户，但没有所需的权限时，会发生此错误。 全局管理员可以创建或删除任何用户，包括其他管理员。 用户管理员可以创建用户并删除任何非管理员用户、支持管理员和其他用户管理员。 |
| *属性 userPrincipalName 无效。* | 有关允许和禁止使用字符的列表，请参阅 [用户名策略](/zh-cn/azure/active-directory/authentication/concept-sspr-policy#userprincipalname-policies-that-apply-to-all-user-accounts)。 在 UPN 中使用不可接受的字符创建新用户时，会发生此错误。 用户名和电子邮件地址属性还不能包含重音字符。 |
| *指定的密码不符合密码复杂性要求。 请提供其他密码。* | 避免使用密码：  - 不遵循 [Microsoft Entra 密码策略](/zh-cn/azure/active-directory/authentication/concept-sspr-policy#password-policies-that-only-apply-to-cloud-user-accounts)。 - 位于 [自定义禁止密码列表](/zh-cn/azure/active-directory/authentication/concept-password-ban-bad#custom-banned-password-list) 上。 - 包含用户的用户名。 |
| *userPrincipalName 属性的域部分无效。 必须在组织中使用已验证的域名之一。* | 请确保用于创建用户的域[在 Microsoft Entra 管理中心的已验证域列表中](/zh-cn/azure/active-directory/fundamentals/add-custom-domain#verify-your-custom-domain-name)。 域的状态需要**验证**。 如果已经验证了域状态，请查看域是**联合**域（有复选标记）还是**托管**域（没有复选标记）。 只能在 Microsoft Entra ID 中为托管域创建用户。 对于联盟域，必须在标识提供者 (IdP) 上创建用户，然后同步到 Microsoft Entra ID。 [无法将联盟域分配给用户。](/zh-cn/office365/troubleshoot/domain-management/cannot-assign-federated-domain-to-user) |

## 目录配额

对于 Microsoft Entra ID 的免费版，默认情况下，可以在单个租户中创建最多 50,000 Microsoft Entra 资源。 如果使用至少一个已验证的域，则组织的默认Microsoft Entra 服务配额将扩展到 300,000 Microsoft Entra 资源。 对于通过自助注册创建的组织，Microsoft Entra 服务配额仍为 50,000 Microsoft Entra 资源。 即使你进行了内部管理员接管并将组织转换为具有一个或多个已验证域的托管租户，此限制也适用。 此服务上限与 Microsoft Entra 定价页上 500,000 个资源的定价层上限无关。 若要超过默认配额，必须联系 Microsoft 支持部门。

有关详细信息，请参阅 [Microsoft Entra 服务限制和限制](/zh-cn/azure/active-directory/enterprise-users/directory-service-limits-restrictions)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/dir-dmns-obj/troubleshoot-user-creation-deletion-issues)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
