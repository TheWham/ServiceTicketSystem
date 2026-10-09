# 使用 Microsoft Graph 将所有者添加到应用程序

对应用程序进行身份验证时，你可能希望能够更新自己的属性，例如客户端密码或证书。 为此，应用程序必须是其自身的所有者。 可以使用 [Microsoft Graph API - 添加所有者](/zh-cn/graph/api/application-post-owners)来实现此功能。

本文概述了使用 Microsoft Graph 将与应用程序关联的服务主体添加为应用程序的所有者所需的权限和分步说明。

## 必需的权限

“ [添加所有者 - 权限](/zh-cn/graph/api/application-post-owners#permissions) ”表中介绍了向应用程序添加所有者的最低特权权限。 这些权限（例如 `Application.ReadWrite.OwnedBy`，允许应用程序管理其所有者的应用程序）。

## 添加所有者

应用程序所有者可以是单个用户、关联的服务主体或其他服务主体。 以下部分介绍如何将相关服务主体作为所有者添加到应用程序。

### 步骤 1：获取应用程序的对象 ID

若要获取要向其添加所有者的应用程序 **的对象 ID** ，请执行以下步骤：

1. 登录到 [Azure 门户](https://portal.azure.com)。
2. 导航到 Microsoft Entra 管理中心。
3. 浏览到“标识”“应用程序”>“应用注册”>。
4. 找到应用程序并复制其 **对象 ID**。

   ![显示应用程序的对象 ID 的屏幕截图。](media/add-owner-for-application-microsoft-graph/application-object-id.png)

### 步骤 2：获取所有者（服务主体的对象 ID）

若要获取与应用程序关联的服务主体 **的对象 ID** ，请执行以下步骤：

1. 登录到 [Azure 门户](https://portal.azure.com)。
2. 导航到 Microsoft Entra 管理中心。
3. 浏览到 **标识**>**应用程序**>**企业注册**。
4. 找到应用程序并复制其 **对象 ID**。

   ![显示服务主体的对象 ID 的屏幕截图。](media/add-owner-for-application-microsoft-graph/service-principle-object-id.png)

### 步骤 3：将所有者添加到应用程序

下面是两种执行此作的方法：

- [方法 1：使用 Microsoft Graph 资源管理器](#method-1-using-microsoft-graph-explorer)
- [方法 2：使用 Microsoft Graph PowerShell](#method-2-using-microsoft-graph-powershell)

#### 方法 1：使用 Microsoft Graph 资源管理器

1. 请访问[Microsoft Graph Explorer](https://developer.microsoft.com/graph/graph-explorer)。
2. 使用具有更新应用程序所有者的必要权限的用户帐户（例如全局管理员或应用程序管理员）登录。
3. 使用以下请求：

   ```
   POST https://graph.microsoft.com/v1.0/applications/{application-object-id}/owners/$ref

   Content-Type: application/json

   {
       "@odata.id": "https://graph.microsoft.com/v1.0/directoryObjects/{service-principal-id}"
   }
   ```

   注释

   将 `{application-object-id}` 替换为应用程序的 **对象 ID**，将 `{service-principal-id}` 替换为服务主体的 **对象 ID**。

   这是 Microsoft Graph 资源管理器中显示的示例：

   [![Microsoft Graph 资源管理器中请求的截图。](media/add-owner-for-application-microsoft-graph/microsoft-graph-api-call.png)](media/add-owner-for-application-microsoft-graph/microsoft-graph-api-call.png#lightbox)

##### 解决禁止访问错误 (403)

在此过程中，可能会遇到以下错误：

```
"error": {
"code": "Authorization_RequestDenied",
"message": "Insufficient privileges to complete the operation.",
"innerError": {
"date": "2021-12-09T17:41:54",
"request-id": "b1909fc0-aa5c-4b43-8a1f-xxxxxxxxxxxx",
"client-request-id": "836e08bb-a12d-4ade-c761-xxxxxxxxxxxx"
}
}
```

若要解决此问题，请在“**修改权限**”选项卡下同意Microsoft Graph 资源管理器的 API 权限 **Application.ReadWrite.All**。

[![显示如何在 Microsoft Graph 资源管理器中修改权限的屏幕截图。](media/add-owner-for-application-microsoft-graph/modify-permissions.png)](media/add-owner-for-application-microsoft-graph/modify-permissions.png#lightbox)

#### 方法 2：使用 Microsoft Graph PowerShell

下面是将所有者添加到应用程序的 Microsoft Graph PowerShell 脚本的示例：

```
Connect-MgGraph -Scopes Application.ReadWrite.All

# Owner
$OwnerServicePrincipalObjectId = "96858eb3-xxxx-xxxx-xxxx-33a6b0dc2430"

# Application to add owner to
$ApplicationObjectId = "b7463aa1-xxxx-xxxx-xxxx-0963d6c00485"

$Owner = @{
 "@odata.id" = "https://graph.microsoft.com/v1.0/directoryObjects/$($OwnerServicePrincipalObjectId)"
}

New-MgApplicationOwnerByRef -ApplicationId $ApplicationObjectId -BodyParameter $Owner
```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/add-owner-for-application-microsoft-graph)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
