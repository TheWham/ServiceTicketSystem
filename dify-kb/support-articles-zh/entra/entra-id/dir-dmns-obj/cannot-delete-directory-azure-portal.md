# 无法通过 Azure 管理门户删除目录

本文可帮助你修复无法从 Azure 门户 Microsoft Entra 扩展中删除目录的问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 2967860

## 现象

无法通过 Azure 管理门户从 Microsoft Entra 扩展中删除目录。 此外，你还会收到以下消息之一：

> 你以公司名称<为主目录的用户>身份登录。

> 删除除自己以外的所有用户。

> 目录具有Microsoft Online Services 的一个或多个订阅。

> 目录具有一个或多个 Azure 订阅。

> 目录具有一个或多个应用程序。

> 目录具有一个或多个多重身份验证提供程序。

> 目录是“合作伙伴”目录。

> 目录包含由用户或管理员添加的一个或多个应用程序。

## 你以公司名称<为主目录的用户>身份登录

确保目录没有主用户，然后删除该目录。 删除此目录的用户必须是来宾用户，必须驻留在另一个目录中，并且必须是要删除的目录的全局管理员。

例如，目录具有域 `contoso.onmicrosoft.com` 和 `contoso.com`。 目录中没有这些域的用户。 来宾用户可能是Microsoft帐户，也可以驻留在另一个目录中，例如 `fabrikam.onmicrosoft.com`。

若要详细了解如何添加来宾用户，请参阅 [“创建或编辑用户](/zh-cn/previous-versions/azure/hh967632(v=azure.100))”。 在目录中创建此用户时，请选择以下项之一：

- 具有现有Microsoft帐户的用户
- 另一个Microsoft Entra 目录中的用户

此用户还必须是 Azure 订阅的管理员。

## 删除除自己以外的所有用户

执行消息告知要执行的操作。 也就是说，删除除自己以外的所有用户。

## 目录具有Microsoft Online Services 的一个或多个订阅

你有以下订阅之一？

- Office 365
- Intune
- 动力学
- Microsoft Azure 信息保护（以前称为 azure 权限管理Microsoft）
- Microsoft Entra ID P1 或 P2

如果你有其中一个订阅，请联系 [计费和订阅支持部门](https://support.office.com/)。

你有以下订阅之一？

- Microsoft 企业移动性 + 安全性
- Microsoft Entra基本

如果你有其中一个订阅，请联系批量许可合作伙伴取消订阅。

## 目录具有一个或多个 Azure 订阅

如果有 Azure 订阅，请确保 Azure 订阅未链接到另一个目录。 为此，请按照下列步骤进行操作：

1. 在导航窗格中，选择“ **设置”**，然后选择“ **订阅**”。
2. 请注意以下信息：

   - 订阅
   - 帐户管理员
   - 目录
3. 如果尝试删除的目录列在任何订阅下，帐户管理员必须登录并更改与订阅关联的目录。 为此，帐户管理员应执行以下步骤：

   1. 在此屏幕上，选择“ **编辑目录**”。
   2. 在“编辑目录”窗口中，选择“目录”列表，然后更改目录。

注意

如果没有其他目录作为选项提供，则帐户管理员必须是另一个目录的全局管理员，或者必须创建新目录。 如果帐户是Microsoft帐户，则会看到“编辑目录”选项。 组织帐户无法更改目录。 因此，无法删除目录。

## 目录具有一个或多个应用程序

若要了解如何从目录中删除应用程序，请阅读 [“添加”、“更新”和“删除应用程序”](/zh-cn/azure/active-directory/develop/quickstart-register-app)

可能还必须删除其他服务主体。 使用 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/installation) 删除所有服务主体：

1. [安装 Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/installation)。
2. `Remove-MgServicePrincipal`运行命令以删除所有服务主体。 要执行此命令，至少需要 `Application.ReadWrite.All` 权限。 有关详细信息，请参阅 [Remove-MgServicePrincipal](/zh-cn/powershell/module/microsoft.graph.applications/remove-mgserviceprincipal?view=graph-powershell-1.0&preserve-view=true)。

   ```
    Connect-MgGraph -Scopes "Application.ReadWrite.All" -tenant <tenant-ID>
    Get-MgServicePrincipal  | ForEach-Object { Remove-MgServicePrincipal -ServicePrincipalId $_.Id }
   ```

   注意

   删除某些服务主体时，可能会收到错误。 无法删除这些主体。 但是，这不会阻止删除目录。 收到的错误可能如下所示：

   Remove-MgServicePrincipal：指定的应用主体 ID 是 Microsoft内部专用。

## 目录具有一个或多个多重身份验证提供程序

删除目录的 Azure 多重身份验证提供程序。 有关如何执行此操作的信息，请参阅 [规划 Azure 多重身份验证部署](/zh-cn/azure/active-directory/authentication/howto-mfa-getstarted)。

## 目录是“合作伙伴”目录

请在Microsoft合作伙伴站点联系 [Microsoft合作伙伴支持人员](https://partner.microsoft.com)。

## 目录包含由用户或管理员添加的一个或多个应用程序

若要解决此问题，请在尝试删除 Microsoft Entra ID [中的 B2C 目录时执行“无法删除”错误中的步骤](https://support.microsoft.com/help/3112170)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/dir-dmns-obj/cannot-delete-directory-azure-portal)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
