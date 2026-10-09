# 排查 Microsoft Entra ID 中的同意问题

## 概要

本文提供有关排查Microsoft Entra ID 中的同意问题的指南。 它适用于基于 OpenID Connect 和 OAuth2 的身份验证。

备注

基于 SAML 的应用程序可能会出现类似的错误，但需要不同的解决方案，这通常是由于第三方 SAML 服务提供商或Microsoft Entra ID 上的 SAML 请求中的配置不匹配。

## 现象

当应用程序尝试登录或获取用户或管理员尚未同意的资源的访问令牌时，会收到类似于以下示例之一的错误消息：

- > 需要管理员批准
- > AADSTS65001：用户或管理员尚未同意使用 ID 为“App-ID<”>的应用程序，名为“<Name-of-App>”。 针对此用户和资源发送交互式授权请求。
- > AADSTS650056：配置错误的应用程序。 这可能是由于以下原因之一：客户端未在客户端的应用程序注册中请求的权限中列出“AAD Graph”的任何权限。 或者，管理员未在租户中表示同意。 或者，检查请求中的应用程序标识符，以确保它与所配置的客户端应用程序标识符匹配。 请联系你的管理员来修复配置或者代表租户来表示同意。
- > AADSTS90094：TenantDisplayName< 的>管理员已设置一个策略，阻止你授予<应用名称>所请求的权限。 请联系 TenantDisplayName< 的>管理员，他们可以代表你向此应用授予权限。
- > AADSTS90008：用户或管理员尚未同意使用 ID 为“App-ID<”>的应用程序。 发生这种情况是因为应用程序配置错误：它必须至少通过指定“登录和读取用户配置文件”权限来访问 Windows Azure Active Directory
- > AADSTS900941: 管理员同意是必需的。 应用被视为有风险。 （AdminConsentRequiredDueToRiskyApp）此应用可能有风险。 如果你信任此应用，请要求管理员授予你访问权限。
- > AADSTS900981: 有风险的应用收到一个管理员同意请求。 （AdminConsentRequestRiskyAppWarning）此应用可能有风险。 仅当你信任此应用时继续。

你可能会收到一条消息，指出需要管理员批准或管理员同意，原因有很多。 请考虑以下高级方案：

- **缺少 User.Read** 权限。
- 在租户级别禁用用户同意。
- 为应用程序启用用户分配。
- 客户端应用程序的租户中不存在服务主体。
- 资源租户中不存在服务主体。
- 指定 `prompt=admin_consent` 或 `prompt=consent` 请求的同意 URL。
- 尚未同意的范围是在登录请求中请求的。
- 范围或权限需要管理员同意。
- 对于有风险的应用程序，用户同意被阻止。

以下部分提供了一个故障排除指南，用于查找同意问题的根本原因。 若要直接解决问题，请转到“ [执行管理员同意](#perform-admin-consent) ”部分。

## 故障排除准备工作

确保应用程序具有用户登录的权限，例如 **User.Read** 权限。 此外，请确保已同意此权限。

例如，如果拥有应用程序注册或任何需要用户登录的应用程序，则至少应具有添加到应用程序注册 **API 权限的 Microsoft Graph **User.Read** 或 **Openid** 委托权限**。

[![显示添加到应用程序注册 API 权限的权限的屏幕截图。](media/troubleshoot-consent-issues/configured-permissions.png)](media/troubleshoot-consent-issues/configured-permissions.png#lightbox)

## 对步骤进行故障排除

### 步骤 1：获取发送到 Microsoft Entra ID 的登录请求

若要确定同意提示出现的原因，请获取登录请求并检查发送到 Microsoft Entra ID 的参数。 出现同意提示时，可以使用以下方法之一获取登录请求：

- 如果使用浏览器，请查看地址栏。
- 如果不使用浏览器，或者仍然看不到浏览器中的地址栏，请使用 Fiddler 等 HTTP 捕获工具来获取请求。

登录请求应如下所示：

- V1 OAuth2 终结点：

  `https://<Aad-Instance>/<Tenant-ID>/oauth2/authorize?client_id=<App-ID>&response_type=code&redirect_uri=<Redirect-URI>&resource=<App-URI-ID>&scope=<Scope>&prompt=<Prompt>`
- V2 OAuth2 终结点：

  `https://<Aad-Instance>/<Tenant-ID>/oauth2/v2.0/authorize?client_id=<App-ID>&response_type=code&redirect_uri=<Redirect-URI>& scope=<Scope>&prompt=<Prompt>`

下表提供了登录请求中使用的参数示例，这些参数在以下故障排除步骤中引用：

| properties | 登录请求部分 | 值 |
| --- | --- | --- |
| Aad-Instance | `<Aad-Instance>` | login.microsoftonline.com |
| Tenant-ID | `<Tenant-ID>` 登录请求的一部分 | 公用 |
| App-ID | `<App-ID>` 登录请求的一部分 | 00001111-aaaa-2222-bbbb-3333cccc4444 |
| Scope | `<Scope>` 登录请求的一部分 | Openid+User.Read+Directory.Read.All |
| App-URI-ID | V1 终结点： `<App-URI-ID>` 登录请求  V2 终结点的一部分：对于除 Microsoft Graph 以外的资源，此部分将是范围名称之前的部分。 例如，`https://analysis.windows.net/powerbi/api/App.Read.All``App.Read.All`为范围名称，因此为 `App-URI-ID` < a0`https://analysis.windows.net/powerbi/api`/>。 | https://graph.microsoft.com |
| 提示 | `<Prompt>` 登录请求的一部分 |  |

### 步骤 2：验证是否允许用户同意

若要检查组织中是否允许用户同意，请执行以下步骤：

1. 登录到 Azure 门户。
2. 导航到Microsoft Entra ID，然后选择**企业应用程序>许可和权限。**
3. **查看用户对应用程序**设置的同意：

   - 如果选择 **了“允许用户同意应用** ”，则所有用户都可以同意不需要管理员同意的权限。 在这种情况下，请转到下一步。
   - 如果选择 **了“不允许用户同意** ”，用户将始终收到“需要管理员批准”消息。 在这种情况下，管理员必须 [执行管理员同意](#perform-admin-consent)。

     备注

     如果管理员认为他们已经同意了这些权限，很可能不是登录请求中列出的所有必需权限都已同意，或者使用了 `<App-ID>`基于错误的应用程序。

### 步骤 3：验证应用程序是否存在

若要验证应用程序是否存在于租户中，请执行以下步骤：

1. 登录到 Azure 门户。
2. 根据 `<Tenant-ID>`该设置切换到正确的租户。
3. 转到“企业应用程序”。
4. 将 **应用程序类型** 设置为 **所有应用程序** 并搜索 `<App-ID>`。
5. 如果未找到应用程序，这就是你遇到同意问题的原因。 在这种情况下， [请执行管理员同意](#perform-admin-consent)。 如果找到应用程序，请转到下一步。

### 步骤 4：验证是否需要用户分配

在“ **企业应用程序** ”窗格中，搜索并选择该应用程序。 在**“管理**”部分下，选择“属性**”**以打开**“属性**”窗格，然后查看**“分配所需的**设置”。

如果需要用户分配，管理员必须同意此应用程序。 为此，请转到 [“执行管理员同意](#perform-admin-consent) ”部分。

备注

同意组织中所有用户的应用程序不允许所有用户访问该应用程序。 必须遵循用户分配规则。 只有分配给应用程序的那些用户才能访问它。 如果不想执行管理员同意，唯一的解决方法是关闭**所需的**分配，要求用户在访问应用程序时同意，然后重新打开**“分配”。**

如果不需要用户分配，请转到下一步。

### 步骤 5：比较为应用程序请求和授予的权限

若要验证登录请求中的作用域（也称为权限）是否列在 **应用程序的“权限** ”部分中，请执行以下步骤：

1. 如果在步骤 3 中找到 [应用程序：验证应用程序是否存在](#step-3-verify-if-the-application-exists)，请选择它。
2. 转到 **“权限**”。
3. 比较“权限**”窗格中列出的**内容，以及登录请求中所列`<Scope>`的内容。 “权限**”窗格中列出的**权限是已同意的权限。

   备注

   - 请注意权限类型。 委托的权限适用于用户登录时，应用程序权限用于使用服务主体通过客户端凭据流进行身份验证。
   - OpenID Connect 范围通常未在企业应用程序中列出。 如果以下范围未列出，请不要担心：

     - `openid`：让用户登录
     - `email`：查看用户的电子邮件地址
     - `profile`：查看用户的基本配置文件
     - `offline_access`：保持对已授予数据访问权限的数据的访问权限
4. 如果在`<Scope>`登录请求中为空或包含的权限窗格中列出的内容小于，请转到下一步。 如果其他 `<Scope>` 作用域不在 **“权限** ”窗格中，请转到“ [执行管理员同意](#perform-admin-consent) ”部分。 必须同意缺少的权限。

### 步骤 6：验证租户中是否存在资源

若要检查资源是否存在，请尝试如下所示 `https://<Aad-Instance>/<Tenant-ID>/oauth2/authorize?response_type=code&client_id=<App-ID>&resource=<App-URI-ID>`的请求。

可能会遇到以下行为或错误之一：

- 你可以登录（这是你期望的行为）。 在这种情况下，请转到下一步。 在大多数情况下，如果在地址栏中看到 `code` 参数，则表示身份验证过程成功。
- 错误AADSTS650052：应用需要访问组织未订阅或启用的服务。 要查看服务订阅的配置，请与 IT 管理员联系。

  此错误表示组织中不存在资源。 若要解决此问题，请使用以下同意 URL： `https://login.microsoftonline.com/<Tenant-ID>/oauth2/authorize?response_type=code&client_id=<App-URI-ID>&prompt=admin_consent`
- 错误AADSTS650057：资源无效。 客户端已请求访问某个资源，但该资源未在客户端应用程序注册中的所需权限中列出。 客户端应用 ID： <App-ID>（<App-Display-Name>）。 请求中的资源值：“<App-URI-ID>”。 资源应用 ID：<Resource-App-ID>。 应用注册中的有效资源列表：00000002-0000-0000-c000-0000000000000

  为了使客户端应用程序登录并获取资源的访问令牌，必须为该资源分配客户端应用程序所需的 API 权限，例如访问 Azure 密钥库。

  ![显示如何将 Azure 密钥库添加到 API 权限的屏幕截图。](media/troubleshoot-consent-issues/azure-key-vault.png)

  备注

  只有应用程序所有者才能执行此操作。
- 错误AADSTS500011：在名为“Tenant-ID<”的租户中找不到名为“>App-URI-ID<”>的资源主体。 如果应用程序尚未由租户管理员安装，或者尚未获得租户中的任何用户同意，则可能会发生这种情况。 可能将身份验证请求发送给了错误的租户。

  此错误表示指定 `<App-URI-ID>` 无效或仅可用作单租户应用程序。 否则，这意味着外部组织无法访问此资源或不存在。

  若要解决此问题，必须与应用程序所有者合作，以验证 `<App-URI-ID>` 其 `<Tenant-ID>` 是否正确。
  `<App-URI-ID>`如果应用由其他`<Tenant-ID>`用户拥有，则必须将应用`<App-URI-ID>`注册设置为多租户应用程序。 否则， `<Tenant-ID>` 该租户必须与应用注册 `<App-URI-ID>` 所在的租户相同。

### 步骤 7：验证是否传递了提示参数

有时，登录到应用程序需要传递`prompt``consent`或 `admin_consent`. 应用程序获得同意后，请确保 `prompt` 未指定参数。 否则，用户可能始终会收到同意错误。

登录请求可能如下所示：

`https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/authorize?client_id=00001111-aaaa-2222-bbbb-3333cccc4444&response_type=code&redirect_uri=https://www.contoso.com&scope=openid+profile+User.Read+Directory.Read.All&prompt=consent`

因此，若要解决同意问题，请删除 `prompt` 参数，如下所示：

`https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/authorize?client_id=00001111-aaaa-2222-bbbb-3333cccc4444&response_type=code&redirect_uri=https://www.contoso.com&scope=openid+profile+User.Read+Directory.Read.All`

## 执行管理员同意

若要解决许可问题，请执行以下步骤执行管理员同意：

1. 让具有全局管理员、公司管理员或应用程序管理员角色的管理员（具有全局管理员、公司管理员或应用程序管理员角色的用户）访问该应用程序。
2. 如果出现许可屏幕，请查看请求的权限。 若要批准请求的权限，请 **选中“代表组织** 同意”复选框。

   ![显示“代表组织同意”复选框的屏幕截图。](media/troubleshoot-consent-issues/consent-on-behalf-of-your-organization.png)

   备注

   如果管理员不确定允许的权限，管理员必须与应用程序供应商合作，以了解权限及其使用。 Microsoft支持可能不知道这些权限做什么或为什么需要这些权限。
3. 如果管理员未获得同意屏幕，请获取登录地址，添加到 `&prompt=consent` 末尾，然后使用此请求执行管理员同意。

   下面是一个示例：`https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/authorize?client_id=00001111-aaaa-2222-bbbb-3333cccc4444&response_type=code&redirect_uri=https://www.contoso.com&scope=openid+profile&tresource=https://graph.microsoft.com&prompt=consent`

   如果应用程序注册中未列出请求的权限，请使用 Microsoft 标识平台 （V2） 终结点强制管理员同意。 V2 终结点要求在参数中 `scope` 传递每个权限范围，如下所示：

   `https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/v2.0/authorize?client_id=00001111-aaaa-2222-bbbb-3333cccc4444&response_type=code&redirect_uri=https://www.contoso.com&scope=openid+profile+User.Read+Directory.Read.All&prompt=consent`

备注

- 应用程序使用的权限范围必须由应用程序所有者提供。
- 对应用程序权限的许可始终需要全局管理员或公司管理员的管理员同意。 必须在应用程序拥有租户的应用程序注册中添加应用程序权限。
- 应用程序管理员还可以同意委托需要管理员同意的权限。
- 使用管理员同意 URL 时，必须已使用应用程序注册配置权限。 否则，应用程序所有者必须正确配置其应用程序，Microsoft Entra ID。 管理员同意 URL 如下所示 `https://login.microsoftonline.com/<Tenant-ID>/adminconsent?client_id=<App-ID>`。

## 详细信息

### 同意

在大多数情况下，某些需要同意的权限尚未获得同意。 因此，请求同意。 若要了解同意，请参阅以下页面：

- [Microsoft 标识平台中的权限和同意概述](/zh-cn/entra/identity-platform/permissions-consent-overview)
- [Microsoft 标识平台管理员同意协议](/zh-cn/entra/identity-platform/v2-admin-consent)
- [Microsoft Entra 应用许可体验](/zh-cn/entra/identity-platform/application-consent-experience)

### 应用程序注册和企业应用程序

在 Microsoft Entra 中，应用程序模型由应用程序对象（也称为“应用程序注册”）和服务主体对象（也称为“企业应用程序”）组成。 根据应用程序对象设置所需的权限，其关系如何协同工作。 有关详细信息，请参阅 [Microsoft Entra ID 中的应用程序对象和服务主体对象](/zh-cn/entra/identity-platform/app-objects-and-service-principals)。

只需向应用程序注册添加权限就不同意权限。 若要同意权限，必须向服务主体分配权限。

### 委派的权限和应用程序权限

Microsoft Entra ID 中有两种类型的权限：委派的权限和应用程序权限。 请确保在应用程序注册中应用正确的权限配置并同意该权限。

有关 Microsoft Entra ID 中的权限的详细信息，请参阅以下页面：

- [Microsoft 标识平台中的权限和同意概述](/zh-cn/entra/identity-platform/permissions-consent-overview)
- [了解 OAuth2 身份验证流中的应用程序和委托权限之间的差异](https://blogs.aaddevsup.xyz/2019/07/understanding-the-difference-between-application-and-delegated-permissions-from-oauth2-authentication-flows-perspective/)

### 收集 Microsoft Entra 活动日志

可以使用 Microsoft Entra 活动日志来获取更多详细信息。 为此，请按照以下步骤操作：

1. 使用有权读取审核日志的帐户（例如全局管理员或安全读取者）登录到Azure 门户。
2. 转到“Microsoft Entra ID”。
3. 在“监视**”部分下**选择“**审核日志**”。
4. 按如下所示设置筛选器：
   - **类别**： **ApplicationManagement**
   - **状态**： **失败**
   - **活动**： **同意应用程序**
5. 查找并选择无法同意的应用。
6. **查看状态原因**以获取更多详细信息。

在某些情况下，需要执行管理员同意，即使你可能允许用户同意，并且权限通常不需要管理员同意。 例如，当状态原因显示“Microsoft.Online.Security.UserConsentBlockedForRiskyAppsException”。有关详细信息，请参阅[在登录到应用程序](/zh-cn/entra/identity/enterprise-apps/application-sign-in-unexpected-user-consent-error#requesting-not-authorized-permissions-error)[时执行同意时出现意外错误和](/zh-cn/entra/identity/enterprise-apps/application-sign-in-unexpected-user-consent-prompt)意外同意提示。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/troubleshoot-consent-issues)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
