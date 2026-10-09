# 尝试使用 New-MSOLDomain 命令将子域添加到现有域时出错：New-MsolDomain：无法添加此域

## 概要

本文提供有关解决“New-MsolDomain：无法添加此域”的指导。 它是一个子域，其身份验证类型与根域的身份验证类型不同。“尝试使用 `New-MSOLDomain` 命令将子域添加到现有域时出错。

*原始产品版本：*云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 用户和域管理、Office 365 标识管理  
*原始 KB 数：* 2666578

## 现象

尝试使用 New-MSOLDomain 命令将子域添加到 Microsoft 云服务（如 Office 365、Microsoft Intune 或 Microsoft Azure）中的现有域。 但是，你会收到以下错误消息：

> New-MsolDomain：无法添加此域。 它是一个子域，其身份验证类型不同于根域的身份验证类型。

注意

自 2024 年 3 月 30 日起，Azure AD 和 MSOnline PowerShell 模块已弃用。 若要了解详细信息，请阅读[有关弃用的更新](https://techcommunity.microsoft.com/t5/microsoft-entra-blog/important-azure-ad-graph-retirement-and-powershell-module/ba-p/3848270)。 在此日期之后，对这些模块的支持仅限于到 Microsoft Graph PowerShell SDK 的迁移帮助和安全性修复。 弃用的模块将持续运行至 2025 年 3 月 30 日。

我们建议迁移到 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview)，以便与 Microsoft Entra ID（以前称为 Azure AD）进行交互。 有关常见迁移问题，请参阅[迁移常见问题解答](/zh-cn/powershell/azure/active-directory/migration-faq)。
*注意：*2024 年 6 月 30 日之后，MSOnline 版本 1.0.x 可能会遇到中断。

## 原因

如果尝试使用 New-MSOLDomain 命令将子域添加到为联合身份验证设置的现有域，则会出现此问题。 New-MSOLDomain 命令尝试将子域添加为标准身份验证域。

## 解决方法

若要将子域添加到为联合身份验证设置的域，请执行以下步骤：

1. 使用 Windows PowerShell 连接到 Microsoft Entra ID。 有关详细信息，请参阅 [使用 Windows PowerShell](/zh-cn/previous-versions/azure/jj151815(v=azure.100)?redirectedfrom=MSDN#bkmk_connect) 连接到 Microsoft Entra ID。
2. 使用 New-MSOLFederatedDomain 命令。

   添加子域的语法如下所示，其中 <子域> 是要添加的子域的名称：

   ```
   New-MSOLFederatedDomain -DomainName:<subdomain>
   ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/new-msoldomain-cmdle-add-subdomain)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
