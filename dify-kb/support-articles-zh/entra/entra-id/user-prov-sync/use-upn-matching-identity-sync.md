# 如何在 Office 365、Azure 或 Intune 中使用 UPN 匹配进行标识同步

*原始产品版本：*Microsoft Entra ID、云服务（Web 角色/辅助角色），Microsoft Intune  
*原始 KB 数：* 3164442

## 概要

有时，如果该帐户最初是使用Microsoft云服务管理工具创作的，则可能需要转移用户帐户的授权来源。 这些工具包括：

- Office 365 门户
- 适用于 Windows PowerShell 的 Azure Active Directory 模块Microsoft
- Azure 管理门户
- Intune 门户

可以传输颁发机构源，以便在将标识同步与 Microsoft Entra ID 配合使用时，可以通过本地目录服务管理该帐户。

本文讨论如何使用称为 **UPN 匹配**的进程执行传输。 此过程使用用户主体名称（UPN）将本地用户帐户与Microsoft Entra ID 中的工作或学校帐户匹配。

## UPN 匹配限制

UPN 匹配过程具有以下技术限制：

- 仅当 SMTP 匹配失败时，才能运行 UPN 匹配。 有关 SMTP 匹配的详细信息，请参阅 [如何使用 SMTP 匹配将本地用户帐户与 Office 365 用户帐户匹配，以便进行目录同步](https://support.microsoft.com/help/2641663)。 若要使 UPN 匹配正常工作，请确保本地用户帐户与 Microsoft Entra ID 中的用户帐户之间没有主 SMTP 地址匹配。
- UPN 匹配只能一次用于最初使用 Office 365 管理工具创作的用户帐户。 之后，工作或学校帐户由不可变标识值（而不是 UPN）绑定到本地用户。
- 云用户的 UPN 无法在 UPN 匹配过程中更新。 这是因为 UPN 是用于将本地用户链接到云用户的值。
- UPN 被视为唯一值。 确保没有两个用户具有相同的 UPN。 否则，同步过程会失败，你可能会收到类似于以下示例的错误消息：

  > 无法在 Microsoft Online Services 中更新此对象，因为本地 Active Directory 中与此对象关联的用户主体名称已与另一个对象关联。 若要解决此错误，请删除本地 Active Directory 中的关联对象。

## 如何使用 UPN 匹配将本地用户与云标识匹配

若要启动 UPN 匹配过程，请执行以下步骤：

1. 如果您在 2016 年 3 月 30 日之前开始同步到 Microsoft Entra ID，请运行以下 [Update-MgDirectoryOnPremiseSynchronization](/zh-cn/powershell/module/microsoft.graph.identity.directorymanagement/update-mgdirectoryonpremisesynchronization) cmdlet，以仅针对您的组织启用 UPN 软匹配。

   有关详细信息，请参阅 [Microsoft Graph PowerShell SDK 入门](/zh-cn/powershell/microsoftgraph/get-started)。

   ```
   Import-Module Microsoft.Graph.Identity.DirectoryManagement

   # Replace with your actual Directory Sync ID
   $onPremisesDirectorySynchronizationId = "<your-directory-sync-id>"

   # Define the parameters to enable SoftMatchOnUpn
   $params = @{
       features = @{
           SoftMatchOnUpnEnabled = $true
       }
   }

   # Run the update
   Update-MgDirectoryOnPremiseSynchronization -OnPremisesDirectorySynchronizationId $onPremisesDirectorySynchronizationId -BodyParameter $params
   ```

   注意

   对于在 2016 年 3 月 30 日或之后开始同步到 Microsoft Entra ID 的组织，将自动启用 UPN 软匹配。
2. 从 Microsoft Entra ID 中的用户帐户获取 UPN。 为此，请使用以下方法之一：

   - 方法 1：使用 Office 365 门户。

     1. 以全局管理员身份登录到 [Office 365 门户](https://portal.office.com) 。
     2. 转到“用户管理”页。
     3. 找到并选择用户。
     4. 记下用户名，即 UPN。
   - 方法 2：使用Azure 门户。

     1. 以全局管理员身份登录到[Azure 门户](https://ms.portal.azure.com)。
     2. 选择 Active Directory 扩展，然后选择目录。
     3. 转到“用户管理”页。
     4. 找到并选择用户。
     5. 记下用户名，即 UPN。
3. 在安装了远程服务器管理工具的域控制器或计算机上，打开Active Directory 用户和计算机。 使用与Microsoft Entra ID 中的目标用户帐户匹配的用户名/UPN 创建用户帐户或更新现有用户帐户。 有关详细信息，请参阅在[Active Directory 用户和计算机中创建用户帐户](/zh-cn/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/dd894463(v=ws.10))。
4. 强制目录同步。 有关详细信息，请参阅 [强制目录同步](https://techcommunity.microsoft.com/t5/itops-talk-blog/powershell-basics-how-to-force-azuread-connect-to-sync/ba-p/887043)。

## 详细信息

有关 UPN 软匹配的详细信息，请参阅 [Microsoft Entra Connect Sync 服务功能](/zh-cn/azure/active-directory/hybrid/how-to-connect-syncservice-features#userprincipalname-soft-match)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/use-upn-matching-identity-sync)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
