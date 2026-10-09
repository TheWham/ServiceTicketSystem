# 使用 Microsoft Graph 排查Authorization\_RequestDenied错误

使用Microsoft图形 API 管理用户时，可能会收到以下错误消息：

> `Authorization_RequestDenied. Insufficient privileges to complete the operation.`

本文演示如何使用 Postman 通过“禁用用户”方案对 Microsoft Graph API 中的错误进行故障排除 `Authorization_RequestDenied` 。

## Authorization\_RequestDenied错误的原因

此错误通常是因为用户或应用没有足够的权限。 若要调用 Graph API，应用注册必须具有以下权限：

- 所需的访问级别的相应Microsoft Entra RBAC 角色。 有关详细信息，请参阅 [Microsoft Entra 内置角色](/zh-cn/entra/identity/role-based-access-control/permissions-reference)。
- 访问 Microsoft Graph 所需的 API 权限。

## 使用 Postman Microsoft 对图形 API 进行故障排除

### 步骤 1：将 Microsoft Entra RBAC 角色分配给应用注册（服务主体）

1. 登录到[Azure 门户](https://portal.azure.com)，并转到**Microsoft Entra ID**。
2. 在 **“管理** ”部分中，选择“ **角色”和“管理员**”。
3. 根据所需的访问级别选择适当的角色。 在本文中，应用将管理用户。 因此， **已选择用户管理员** 。
4. 选择 **“添加分配**”，选择应用注册，然后选择“ **添加**”。

### 步骤 2：查找应用的应用程序 ID、客户端密码和令牌终结点

1. 在[Azure 门户](https://portal.azure.com)中，转到**应用注册**，然后选择应用注册。
2. 在“概述”页上，记录“应用程序(客户端) ID”。
3. 选择“终结点”。 此选择提供将在 Postman 配置中使用的信息，例如令牌终结点。 本文使用 OAuth 2.0 和基于令牌的身份验证以及 Entra ID。 在这种情况下，应记录 **OAuth 2.0 令牌终结点（v2）。**

   [![显示检查应用注册终结点的屏幕截图。](media/troubleshoot-authorization-requestdenied-graph-api/check-endpoints.png)](media/troubleshoot-authorization-requestdenied-graph-api/check-endpoints.png#lightbox)
4. 在 **“管理** ”部分中，选择“ **证书和机密**”。 创建客户端密码或使用现有的客户端密码进行测试。

   在 Postman 配置中，请确保使用客户端机密值，而不是机密 ID。 无法查看客户端机密值，但创建客户端机密值后立即除外。

### 步骤 3：配置 Postman

1. 在 Postman 中，选择请求或集合，然后选择“ **授权**”。
2. 将身份验证类型设置为 **OAuth 2.0**。
3. 在 **“配置新令牌** ”部分中，指定以下配置：

   - 授予类型：客户端凭据
   - 访问令牌 URL： <OAuth 2.0 令牌终结点>。
   - 客户端 ID： <应用程序（客户端）ID>
   - 客户端机密： <客户端机密值>
   - 范围：`https://graph.microsoft.com/.default`
   - 客户端身份验证：以基本身份验证标头的形式发送

   [![Postman 配置的屏幕截图。](media/troubleshoot-authorization-requestdenied-graph-api/postman-config.png)](media/troubleshoot-authorization-requestdenied-graph-api/postman-config.png#lightbox)
4. 选择**获取新访问令牌**。 如果配置正确，应会收到用于运行Microsoft图形 API 调用的令牌。
5. 选择“继续”**，然后选择“**使用令牌**”。**

### 步骤 4：测试和排查Microsoft图形 API 问题

1. 发送以下 PATCH 请求以禁用用户。
   `1f953789-0000-0000-0000-6f21508fd4e2` 是 Entra ID 中用户的对象 ID。

   ```
   Patch https://graph.microsoft.com/v1.0/users/1f953789-0000-0000-0000-6f21508fd4e2
   ```

   ```
   {
   "accountEnabled": false
   }
   ```
2. `Authorization_RequestDenied`响应中收到错误消息：

   ```
   {
       "error": {
           "code": "Authorization_RequestDenied",
           "message": "Insufficient privileges to complete the operation.",
           "innerError": {
               "date": "2024-12-24T03:25:32",
               "request-id": "096361b2-75be-479b-b421-078610030949",
               "client-request-id": "096361b2-75be-479b-b421-078610030949"
           }
       }
   }
   ```
3. 在 [Microsoft Graph REST API v1.0 终结点参考](/zh-cn/graph/api/user-update?view=graph-rest-1.0&tabs=http#permissions&preserve-view=true)中检查更新用户方案。 启用和禁用用户需要以下权限，如 Microsoft Graph REST API v1.0 终结点引用中所述。

   | 属性 | 类型 | 说明 |
   | --- | --- | --- |
   | accountEnabled | 布尔 | `true` 如果帐户已启用，则为否则，为 `false`. 创建用户时，此属性是必需的。   - *User.EnableDisableAccount.All* + *User.Read.All* 是更新此属性所需的权限的最低特权组合。   - 在委派方案中， *特权身份验证管理员* 是允许为租户中的所有管理员更新此属性的最低特权角色。 |
4. 检查应用注册是否具有所需的权限：

   1. 在Azure 门户中找到应用注册。
   2. 在 **“管理** ”部分中，选择 **API 权限**
   3. 检查配置的 API 权限。 在这种情况下，应用注册没有 **User.EnableDisableAccount.All** 权限，这是问题的根本原因。

      [![显示检查 API 权限的屏幕截图。](media/troubleshoot-authorization-requestdenied-graph-api/check-api-permissions.png)](media/troubleshoot-authorization-requestdenied-graph-api/check-api-permissions.png#lightbox)
5. 选择“**添加权限**”，将 User.EnableDisableAccount.All **添加到**应用注册。
6. 还必须为权限的默认目录**选择**“授予管理员许可”。 选择“是”确认要授予管理员同意。
7. 发送 PATCH 请求以禁用用户。 如果请求成功，应会收到 `204 No Content` 响应。

**第三方信息免责声明**

本文中提到的第三方产品由 Microsoft 以外的其他公司提供。 Microsoft 不对这些产品的性能或可靠性提供任何明示或暗示性担保。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/troubleshoot-authorization-requestdenied-graph-api)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
