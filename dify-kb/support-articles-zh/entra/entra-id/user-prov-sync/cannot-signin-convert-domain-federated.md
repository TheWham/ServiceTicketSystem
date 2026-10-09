# 运行 Convert-MSOLDomaintoFederated 命令以转换现有域后，用户无法再登录

## 概要

本文提供有关在运行 `Convert-MSOLDomaintoFederated` 命令以将现有域从标准身份验证转换为联合身份验证后，无法再访问 Office 365、Azure 或 Microsoft Intune 的问题。

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2662960

注意

自 2024 年 3 月 30 日起，Azure AD 和 MSOnline PowerShell 模块已弃用。 若要了解详细信息，请阅读[有关弃用的更新](https://techcommunity.microsoft.com/t5/microsoft-entra-blog/important-azure-ad-graph-retirement-and-powershell-module/ba-p/3848270)。 在此日期之后，对这些模块的支持仅限于到 Microsoft Graph PowerShell SDK 的迁移帮助和安全性修复。 弃用的模块将持续运行至 2025 年 3 月 30 日。

我们建议迁移到 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview)，以便与 Microsoft Entra ID（以前称为 Azure AD）进行交互。 有关常见迁移问题，请参阅[迁移常见问题解答](/zh-cn/powershell/azure/active-directory/migration-faq)。
*注意：*2024 年 6 月 30 日之后，MSOnline 版本 1.0.x 可能会遇到中断。

## 现象

在Microsoft云服务（如 Office 365、Microsoft Azure 或 Microsoft Intune）中设置单一登录（SSO）期间，运行 `Convert-MSOLDomaintoFederated` 该命令将现有域从标准身份验证转换为联合身份验证。 但是，执行此操作后，与该域关联的用户将无法再访问云服务。

## 原因

如果未正确设置 SSO，或者安装未完成，则会出现此问题。

警告

最佳做法 Microsoft是始终至少有一个与默认域关联的管理员用户 ID，以便在 SSO 遭到入侵时不会丢失对组织的管理访问权限。

## 解决方法

若要解决此问题，请根据需要使用以下方法之一。

### 方法 1：排查 SSO 设置问题

仅当以下所有条件均为 true 时，才使用此方法：

- 问题不是由服务中断引起的。
- 无需立即还原用户访问权限。

若要诊断和排查 SSO 设置问题，请参阅 [排查 Office 365、Intune 或 Azure](https://support.microsoft.com/help/2530569) 中的单一登录设置问题。

### 方法 2：如果 AD FS 服务器不可用，请将域联合还原为标准身份验证

仅当以下所有条件均为 true 时，才使用此方法：

- 此问题是由需要立即还原用户访问的服务中断引起的。
- AD FS 服务器不可用。

如果这些条件为 true，请重置域和每个用户帐户的身份验证设置以使用标准身份验证。 为此，请按照下列步骤进行操作：

1. 启动适用于 Windows PowerShell 的 Azure Active Directory 模块。 为此，请选择“开始”**，选择“**所有**程序”，选择**“Windows Azure Active Directory”，右键单击 **Windows PowerShell** 的 Windows Azure Active Directory** 模块，然后选择“**以管理员**身份**运行”。
2. 若要转换域，请按照显示域的顺序运行以下命令。 键入每个命令后按 Enter。

   ```
   $cred = Get-Credential
   ```

   出现提示时，请输入未启用 SSO 的云服务管理员凭据。

   ```
   Connect-MsolService -credential $cred
   ```

   ```
   Set-MSOLDomainAuthentication -Authentication Managed -DomainName <federated domain name>
   ```

   注意

   在此命令中，占位符 <联合域名> 表示 SSO 不起作用的域的名称。
3. 对于具有与域关联的用户主体名称（UPN）后缀的每个用户，请运行以下命令：

   ```
   Convert-MSOLFederatedUser -UserPrincipalName <string>
   ```

   注意

   在此命令中，占位符 <字符串> 表示正在转换的用户的 UPN 的值。

## 详细信息

重要

在最后一个Microsoft云服务组织管理员分配联合域的域后缀以及该管理员启用 SSO 的情况下，后续 AD FS 失败将限制运行 connect-MSOLService 命令，并可能阻止解决 SSO 问题。 最佳做法建议Microsoft云服务组织管理员始终保留至少一个未启用 SSO 的全局管理员帐户，以便使用适用于 Windows PowerShell 的 Azure Active Directory 模块来排查 SSO 问题。

如果出现此问题，请联系Microsoft 支持部门暂时撤消域联合，以便管理员（不再启用 SSO）可以重新获得对 SSO 相关问题进行故障排除的权限。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/cannot-signin-convert-domain-federated)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
