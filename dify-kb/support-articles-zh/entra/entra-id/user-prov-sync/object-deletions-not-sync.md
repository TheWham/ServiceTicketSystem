# 使用 Microsoft Entra ID Connect 时，对象删除不会同步到 Microsoft Entra ID

## 概要

本文提供有关解决以下问题的指导：在 Office 365、Azure 或 Microsoft intune 中使用目录同步时，不会从 Microsoft Entra ID 中删除已删除的本地 Active Directory 对象。

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2709902

## 现象

假设出现了下面这种情景：

- 你有一个本地 Active Directory 对象。
- 目录同步用于将 Active Directory 对象同步到 Microsoft Entra ID。 这会创建一个链接对象。
- 你删除本地 Active Directory 对象。

在此方案中，不会从 Microsoft Entra ID 中删除链接对象。

## 原因

如果满足下列任一条件，则可能会出现此问题：

- 尚未进行目录同步。
- 目录同步意外无法删除特定的云对象，并导致孤立Microsoft Entra 对象。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 确保已安装 [Microsoft Graph PowerShell 模块](/zh-cn/powershell/microsoftgraph/installation) 和 [ADSyncTools PowerShell 模块](/zh-cn/azure/active-directory/hybrid/connect/reference-connect-adsynctools) 。
2. 运行以下 ADSync 命令以强制目录同步：

   ```
   Start-ADSyncSyncCycle -PolicyType Initial
   ```
3. 如果同步正常工作，但 Active Directory 对象删除仍未传播到 Microsoft Entra ID，请手动删除孤立对象。 为此，请使用以下Microsoft Graph PowerShell cmdlet 之一：

   - [Remove-MgUserContact](/zh-cn/powershell/module/microsoft.graph.personalcontacts/remove-mgusercontact)
   - [Remove-MgGroup](/zh-cn/powershell/module/microsoft.graph.groups/remove-mggroup)
   - [Remove-MgUser](/zh-cn/powershell/module/microsoft.graph.users/remove-mguser)

   例如，要手动删除最初是通过使用目录同步创建的孤立用户 ID `john.smith@contoso.com`，你需要运行以下 cmdlet：

   ```
   $user = Get-MgUser -Filter "userPrincipalName eq 'john.smith@contoso.com'"
   Remove-MgUser -UserId $user.id
   ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/object-deletions-not-sync)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
