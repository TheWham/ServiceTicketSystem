# 验证登录报告中的第一方 Microsoft 应用程序

## 总结

查看登录报表时，可能会看到一个你并不拥有但想要标识的应用程序。 如果你不记得访问该应用，你可能还想知道如何登录到该应用。

下面是一个登录报告示例：

![Microsoft Entra ID 中登录报告的屏幕截图。](media/verify-first-party-apps-sign-in/sign-in-report.png)

例如，当您访问`learn.microsoft.com`时，登录日志中显示的应用程序可能会显示`dev-rel-auth-prod`，但这并不能清楚地描述`learn.microsoft.com`。

尽管登录报告中列出的应用由Microsoft拥有，并且不是可疑应用程序，但你可以确定Microsoft是否拥有在 Microsoft Entra 日志中找到的 Microsoft Entra 服务主体。

备注

Microsoft 的第一方应用程序并不总会在租户中创建服务主体。 在这种情况下，您可能会继续在登录报告中看到这些应用程序。

## 验证 Microsoft Entra 租户中的第一方微软服务主体

1. 在 [Microsoft Entra ID](https://portal.azure.com/#blade/Microsoft_AAD_IAM/StartboardApplicationsMenuBlade/AllApps/menuId/) 中打开企业应用程序列表。
2. 在导航窗格中，选择“ **所有应用程序**”。
3. 在 **“应用程序类型”** 下拉列表中，选择 **Microsoft 应用程序**，然后选择 **应用**。 此处列出的所有应用程序都归Microsoft所有。

   ![“应用程序类型”下拉菜单的屏幕截图，其中选择了Microsoft应用程序。](media/verify-first-party-apps-sign-in/microsoft-applications-in-application-type-menu.png)
4. 在下拉列表下方的搜索框中，通过添加特定的 **显示名称** 或 **应用程序 ID** 筛选Microsoft应用程序列表。

   ![输入显示名称的搜索框的屏幕截图。](media/verify-first-party-apps-sign-in/add-display-name-in-searchbox.png)
5. 选择所需的应用，然后在导航窗格中选择“属性**”**以查看列出的应用的属性。 验证是否看到以下错误消息：

   ```
   You can't delete this application because it's a Microsoft first party application.
   ```

   ![显示消息的屏幕截图：该消息指出无法删除此应用程序，因为它是 Microsoft 的第一方应用程序。](media/verify-first-party-apps-sign-in/you-cant-delete-this-application.png)

## 通过 PowerShell 验证第一方Microsoft服务主体

### 使用 Microsoft Graph PowerShell SDK 连接到 Microsoft Entra ID

1. 打开 PowerShell，导入 Microsoft Graph PowerShell SDK，然后连接到 Microsoft Entra ID：

   ```
   Import-Module Microsoft.Graph.Applications
   Connect-MgGraph
   ```
2. 在 PowerShell 命令行中，输入应用程序的显示名称并运行以下 cmdlet：

   ```
   $appDisplayName = '<display name>'
   Get-MgServicePrincipal -Filter "DisplayName eq '$appDisplayName'" | Select-Object Id, DisplayName, SignInAudience, AppOwnerOrganizationId
   ```
3. 查看输出中`AppOwnerTenantId`的值。

   ![通过 Microsoft Graph PowerShell SDK 显示Microsoft Entra 服务主体的请求输出的屏幕截图。](media/verify-first-party-apps-sign-in/review-the-app-owner-tenant-id-microsoft-graph.png)

   在屏幕截图中，`f8cdef31-a31e-4b4a-93e4-5f571e91255a` 是微软服务的 Microsoft Entra 租户 ID。

### 使用 Microsoft Entra PowerShell 连接到 Microsoft Entra ID

1. 打开 PowerShell，导入 Microsoft Graph PowerShell SDK 并连接到 Microsoft Entra ID：

   ```
   Import-Module Microsoft.Entra
   Connect-Entra
   ```
2. 在 PowerShell 命令行中，输入应用程序的显示名称并运行以下 cmdlet：

   ```
   $appDisplayName = '<display name>'
   Get-EntraServicePrincipal -SearchString $appDisplayName | Select-Object Id, DisplayName, SignInAudience, AppOwnerOrganizationId
   ```
3. 查看结果`AppOwnerTenantId`。

   ![通过 Microsoft Entra PowerShell 显示Microsoft Entra 服务主体的请求输出的屏幕截图。](media/verify-first-party-apps-sign-in/review-the-app-owner-tenant-id-microsoft-entra.png)

   在屏幕截图中，`f8cdef31-a31e-4b4a-93e4-5f571e91255a` 是微软服务的 Microsoft Entra 租户 ID。

## Microsoft 租户自有应用的应用程序 ID

下表列出了一些（但并非全部）Microsoft租户拥有的应用程序（租户 ID：72f988bf-86f1-41af-91ab-2d7cd011db47）。

| 应用程序名称 | 应用程序 ID |
| --- | --- |
| 图表资源管理器 | de8bc8b5-d9f9-48b1-a8ad-b748da725064 |
| Microsoft Graph 命令行工具 | 14d82eec-204b-4c2f-b7e8-296a70dab67e |
| Outlook用户设置消费者 | 7ae974c5-1af7-4923-af3a-fb1fd14dcb7e |
| Vortex [已启用 wsfed] | 5572c4c0-d078-44ce-b81c-6cbf8d3ed39e |

## 详细信息

有关详细信息，请参阅 [Microsoft Entra 管理中心内的登录活动报告](/zh-cn/azure/active-directory/reports-monitoring/concept-sign-ins#sign-ins-report)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/governance/verify-first-party-apps-sign-in)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
