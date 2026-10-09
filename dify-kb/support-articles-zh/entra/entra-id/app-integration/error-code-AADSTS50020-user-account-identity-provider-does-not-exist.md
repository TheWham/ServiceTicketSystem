# AADSTS50020错误 - 租户中不存在来自标识提供者的用户帐户

## 概要

本文旨在帮助你解决当来自身份提供者（IdP）的来宾用户无法登录到 Microsoft Entra ID 的资源租户时，返回的错误代码 `AADSTS50020`。

## 现象

当来宾用户尝试访问资源租户中的应用程序或资源时，登录将失败，并显示以下错误消息：

> AADSTS50020：来自标识提供者 {IdentityProviderURL} 的用户帐户“user@domain.com”在租户 {ResourceTenantName} 中不存在。

当管理员查看主租户上的登录日志时，“90072”错误代码条目表示登录失败。 错误消息指出：

> 来自标识提供者 {idp} 的用户帐户 {email} 在租户 {tenant} 中不存在，并且无法访问该租户中的应用程序 {appId}（{appName}）。 首先需要将该帐户作为外部用户添加到租户中。 注销并使用另一 Microsoft Entra 用户帐户再次登录。

## 原因 1：用户使用个人Microsoft帐户登录到 Microsoft Entra 管理中心

尝试使用个人Microsoft帐户（Outlook、Hotmail 或 OneDrive）登录到 Microsoft Entra 管理中心时，默认连接到Microsoft服务租户。 在默认租户中，没有用于执行任何操作的链接目录。 这是预期的行为。

在以前的体验中，将创建一个目录（例如：UserNamehotmail735.onmicrosoft.com），并将其链接到个人帐户，你可以执行操作，例如在目录中创建用户帐户。 行为现已更改。

### 解决方案：使用新租户创建 Azure 帐户

如果打算有一个目录，则必须创建一个 Azure 帐户和一个新租户：

1. 浏览到 [Azure 帐户网站](https://azure.microsoft.com/pricing/purchase-options/azure-account?cid=msft_learn)，然后选择“ **免费试用 Azure**”。
2. 按照说明创建 Azure 帐户。
3. 租户将与 Azure 帐户一起生成，你将被自动指定为全局管理员。 这会授予你对此租户中的所有选项的完全访问权限。

## 原因 2：使用了不受支持的帐户类型（多租户和个人帐户）

如果应用注册设置为单租户帐户类型，则来自其他目录或标识提供者的用户无法登录到该应用程序。

### 解决方案：更改应用注册清单中的登录受众设置

若要确保应用注册不是单租户帐户类型，请执行以下步骤：

1. 在 [Azure 门户](https://portal.azure.com)中，搜索并选择“应用注册”。
2. 选择应用注册的名称。
3. 在边栏中，选择**清单**。
4. 在 JSON 代码中，找到 **signInAudience** 设置。
5. 检查设置是否包含以下值之一：

   - **Azure AD 和个人 Microsoft 帐户**
   - **AzureADMultipleOrgs**
   - **个人Microsoft账户**

   **如果 signInAudience** 设置不包含这些值之一，请通过选择正确的帐户类型重新创建应用注册。 当前无法在清单中更改 **signInAudience** 。

有关如何注册应用程序的详细信息，请参阅[快速入门：将应用程序注册到Microsoft 标识平台](/zh-cn/azure/active-directory/develop/quickstart-register-app)。

## 原因 3：使用了错误的终结点（个人和组织帐户）

如果应用注册支持的帐户类型设置为以下值之一，身份验证调用必须以与所选内容匹配的 URL 为目标：

- **任何组织目录中的帐户（任意 Microsoft Entra 目录 - 多租户）**
- **任何组织目录中的帐户（任何Microsoft Entra 目录 - 多租户）和个人Microsoft帐户（例如 Skype、Xbox）**
- **仅限个人Microsoft帐户**

如果使用 `https://login.microsoftonline.com/<YourTenantNameOrID>`，则来自其他组织的用户无法访问该应用程序。 必须在请求中指定的租户中将这些用户添加为来宾。 在这种情况下，预计身份验证将仅在你的租户上运行。 如果希望用户使用与其他租户或标识提供者的联合身份验证登录，则此方案会导致登录错误。

### 解决方案：使用正确的登录 URL

对特定应用程序类型使用相应的登录 URL，如下表所示：

| 应用程序类型 | 登录 URL |
| --- | --- |
| 多租户应用程序 | `https://login.microsoftonline.com/organizations` |
| 多租户和个人帐户 | `https://login.microsoftonline.com/common` |
| 只限个人账户 | `https://login.microsoftonline.com/consumers` |

在应用程序代码中，将此 URL 值应用在设置 `Authority` 中。 有关详细信息`Authority`，请参阅[Microsoft 标识平台应用程序配置选项](/zh-cn/azure/active-directory/develop/msal-client-application-configuration#authority)。

## 原因 4：登录到了错误的租户

当用户尝试访问应用程序时，要么将直接链接发送到应用程序，要么尝试通过该 <https://myapps.microsoft.com>链接获取访问权限。 在任一情况下，用户都会被重定向到应用程序的登录页面。 在某些情况下，用户可能已经有一个活动会话，该会话使用不同于预期使用的个人帐户。 或者，他们在会话中使用了组织帐户，而其实本来想使用个人来宾帐户，或者反过来亦然。

若要确保这种情况是问题，请在错误消息中查找 `User account` 和 `Identity provider` 值。 这些值是否与预期的组合匹配？ 例如，用户是否使用其组织帐户登录到您的租户，而不是其主租户？ 或者用户是否使用与已邀请的个人帐户不同的帐户登录到`live.com`标识提供者？

### 解决方案：注销，然后从其他浏览器或专用浏览器会话再次登录

指示用户打开新的专用浏览器会话，或者让用户尝试从其他浏览器访问。 在这种情况下，用户必须从当前会话中注销，然后再次尝试登录。

## 原因 5：未邀请来宾用户

尝试登录的访客用户未被邀请加入租户。

### 解决方案：邀请来宾用户

请确保按照快速入门中的[步骤操作：将来宾用户添加到Azure 门户](/zh-cn/azure/active-directory/external-identities/b2b-quickstart-add-guest-users-portal)中的目录以邀请来宾用户。

## 原因 6：应用需要用户分配

如果应用程序是需要用户分配的企业应用程序，则如果用户不在分配应用程序访问权限的允许用户列表中，则会发生错误 `AADSTS50020` 。 若要检查企业应用程序是否需要用户分配，请执行以下操作：

1. [在 Azure 门户中](https://portal.azure.com)，搜索并选择**“企业应用程序**”。
2. 选择企业应用程序。
3. 在边栏中，选择“ **属性**”。
4. 检查**需要指定**选项是否设置为**是**。

### 解决方案：单独或作为组的一部分向用户分配访问权限

使用以下选项之一向用户分配访问权限：

- 若要单独向应用程序分配用户访问权限，请参阅 [向企业应用程序](/zh-cn/azure/active-directory/manage-apps/add-application-portal-assign-users#assign-a-user-account-to-an-enterprise-application)分配用户帐户。
- 如果要为属于指定组或动态组的用户进行分配，请参阅 [管理对应用程序](/zh-cn/azure/active-directory/manage-apps/what-is-access-management)的访问权限。

## 原因 7：尝试使用资源所有者密码凭据流用于个人帐户

如果用户尝试将资源所有者密码凭据 （ROPC） 流用于个人帐户，则会发生错误`AADSTS50020`。 Microsoft 标识平台仅在 Microsoft Entra 租户中支持 ROPC，不支持个人帐户。

### 解决方案：使用特定于租户或组织的端点

使用租户专用的终结点（`https://login.microsoftonline.com/<TenantIDOrName>`）或组织的终结点。 受邀加入 Microsoft Entra 租户的个人帐户不能使用 ROPC。 有关详细信息，请参阅 [Microsoft 标识平台和 OAuth 2.0 资源所有者密码凭据](/zh-cn/azure/active-directory/develop/v2-oauth-ropc)。

## 原因 8：以前删除的用户名由主租户管理员重新创建

如果资源租户中已删除的来宾用户名称被主租户的管理员重新创建，可能会出现错误 `AADSTS50020` 。 若要验证资源租户中的来宾用户帐户是否未与主租户中的用户帐户相关联，请使用以下选项之一：

### 验证：使用以下工具来验证Microsoft Entra ID 中的来宾用户状态

若要检查资源租户的来宾用户是否早于主租户的用户帐户，可以使用 Microsoft Graph、Microsoft Entra PowerShell 或 Microsoft Graph PowerShell SDK。

#### Microsoft Graph

向 [MS Graph API](/zh-cn/graph/api/user-get) 发出请求以查看用户创建日期，如下所示：

```
GET https://graph.microsoft.com/v1.0/users/{id | userPrincipalName}/createdDateTime
```

然后，对比资源租户中的来宾用户创建日期和主租户用户帐户的创建日期。 如果来宾用户是在家庭租户用户帐户创建之前创建的，则确认此情况。

#### Microsoft Entra PowerShell

运行 [Get-EntraUser](/zh-cn/powershell/module/microsoft.entra.users/get-entrauser) PowerShell cmdlet 以查看用户创建日期，如下所示：

```
Get-EntraUser -UserId {id | userPrincipalName} | Select-Object id, userPrincipalName, createdDateTime
```

然后，对比资源租户中的来宾用户创建日期和主租户用户帐户的创建日期。 如果来宾用户是在家庭租户用户帐户创建之前创建的，则确认此情况。

#### Microsoft Graph PowerShell SDK

运行 [Get-MgUser](/zh-cn/powershell/module/microsoft.graph.users/get-mguser) PowerShell cmdlet 以查看用户创建日期，如下所示：

```
$p = @('Id', 'UserPrincipalName', 'CreatedDateTime')
Get-MgUser -UserId {id | userPrincipalName} -Property $p| Select-Object $p
```

然后，对比资源租户中的来宾用户创建日期和主租户用户帐户的创建日期。 如果来宾用户是在家庭租户用户帐户创建之前创建的，则确认此情况。

### 解决方案：重置来宾用户帐户的兑换状态

重置资源租户中来宾用户帐户的兑换状态。 然后，可以保留来宾用户对象，而无需删除，然后重新创建来宾帐户。 可以使用 Azure 门户、Azure PowerShell 或 Microsoft 图形 API 重置兑换状态。 关于操作说明，请参阅 [来宾用户重置兑换状态](/zh-cn/azure/active-directory/external-identities/reset-redemption-status)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-AADSTS50020-user-account-identity-provider-does-not-exist)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
