# 无法管理或删除通过 Azure Active Directory 同步工具同步的对象

## 概要

本文介绍无法从 Microsoft Entra ID 管理或删除通过目录同步创建的对象的问题。 它根据不同的原因提供此问题的两个解决方法。

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2619062

## 现象

尝试从 Microsoft Entra ID 手动管理或删除通过目录同步创建的对象：

例如，你希望从本地 Active Directory域服务（AD DS）中删除同步到Microsoft Entra ID 的孤立用户帐户。

在此方案中，无法在 Office 365、Azure 或 Microsoft Intune 中使用 Microsoft 云服务门户或使用 Windows PowerShell 删除孤立用户帐户。

## 原因

如果出现下述一个或多个情况，则可能发生此问题：

- 本地 AD DS 不再可用。 因此，无法从本地环境管理或删除对象。
- 已从本地 AD DS 中删除对象。 但是，该对象不会从云服务组织中删除。 此行为是意外的。

## 解决方法

### 本地 AD DS 不再可用。 因此，无法从本地环境管理或删除对象

想要管理 Office 365、Azure 或 Intune 中的对象，并且不再想要使用目录同步。

1. 确保 [已安装 Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/installation)。
2. 使用 `Connect-MgGraph` 命令通过所需的权限范围登录，例如 `Organization.ReadWrite.All`。 有关详细信息，请参阅 [Microsoft Graph PowerShell SDK 入门](/zh-cn/powershell/microsoftgraph/get-started)。
3. 通过运行 [Update-MgOrganization](/zh-cn/powershell/module/microsoft.graph.identity.directorymanagement/update-mgorganization) 命令禁用目录同步。

   ```
   $organizationId = (Get-MgOrganization).Id

   $params = @{
   onPremisesSyncEnabled = $False
   }

   Update-MgOrganization -OrganizationId $organizationId -BodyParameter $params
   ```
4. 检查是否已完全禁用目录同步。 若要执行此操作，请运行以下命令：

   ```
    Get-MgOrganization | Select OnPremisesSyncEnabled
   ```

   此命令将返回 **True** 或 **False**。 继续定期运行此命令，直到返回 **False**，然后转到下一步。

   停用可能需要 72 小时才能完成。 时间取决于云服务订阅帐户中的对象数。
5. 尝试使用 Windows PowerShell 或云服务门户更新对象。

   步骤 3 可能需要一段时间才能完成。 云服务环境中有一个计算属性值的过程。 必须先完成该过程，然后才能使用 Windows PowerShell 或云服务门户更改对象。

### 从本地 AD DS 中删除对象。 但是，不会从云服务订阅帐户中删除该对象

使用本文中的步骤强制目录同步： [启动计划程序](/zh-cn/azure/active-directory/hybrid/how-to-connect-sync-feature-scheduler#start-the-scheduler)

- 如果传播某些更新和删除，但某些删除不会同步到云服务，请遵循典型的目录同步故障排除过程。
- 如果所有更新和删除未同步到云服务，请联系支持人员。

  注意

  作为此方案的替代解决方案，可以在云服务中手动删除对象。 但是，无法在云服务中更新对象。 有关如何解决此问题的详细信息，请参阅以下Microsoft知识库文章： [使用 Azure Active Directory 同步工具](https://support.microsoft.com/help/2709902)时，对象删除不会同步到Microsoft Entra ID。

## 详细信息

若要重新启用目录同步，请运行以下命令：

```
$organizationId = (Get-MgOrganization).Id

$params = @{
onPremisesSyncEnabled = $True
}

Update-MgOrganization -OrganizationId $organizationId -BodyParameter $params
```

重新启用目录同步时，请务必仔细规划。 如果使用云服务门户或 Windows PowerShell 直接对最初从本地 AD DS 同步的对象进行任何更改，则本地属性和设置将在重新启用目录同步后首次发生同步时被本地属性和设置覆盖。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/cannot-manage-objects)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
