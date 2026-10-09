# 无法使用适用于 Windows PowerShell 的 Azure Active Directory 模块连接到 Office 365、Azure 或 Intune

本文介绍了无法使用 `Connect-MSOLService` cmdlet 连接到 Microsoft 云服务（如 Office 365、Azure 或 Microsoft Intune）的问题 。

注意

自 2024 年 3 月 30 日起，Azure AD 和 MSOnline PowerShell 模块已弃用。 若要了解详细信息，请阅读[有关弃用的更新](https://techcommunity.microsoft.com/t5/microsoft-entra-blog/important-azure-ad-graph-retirement-and-powershell-module/ba-p/3848270)。 在此日期之后，对这些模块的支持仅限于到 Microsoft Graph PowerShell SDK 的迁移帮助和安全性修复。 弃用的模块将持续运行至 2025 年 3 月 30 日。

我们建议迁移到 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview)，以便与 Microsoft Entra ID（以前称为 Azure AD）进行交互。 有关常见迁移问题，请参阅[迁移常见问题解答](/zh-cn/powershell/azure/active-directory/migration-faq)。
*注意：*2024 年 6 月 30 日之后，MSOnline 版本 1.0.x 可能会遇到中断。

*原始产品版本：*Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 用户和域管理、Office 365 标识管理  
*原始 KB 数：* 2494043

## 现象

尝试使用 `Connect-MSOLService` Windows PowerShell Microsoft Azure Active Directory 模块中的 cmdlet 连接到 office 365、Microsoft Azure 或 Microsoft Intune 等Microsoft云服务时，尝试失败。 此外，你会收到以下错误消息之一：

> Connect-MsolService：引发类型为“Microsoft.Online.Administration.Automation.MicrosoftOnlineException”的异常。

> Connect-MsolService：访问被拒绝。 您没有调用此 cmdlet 的权限。

> Connect-MsolService：用户名或密码不正确。 验证您的用户名，并再次输入您的密码。`

## 解决方法

要解决此问题，请根据您的情况参阅以下文章之一：

- [“Connect-MsolService：引发类型异常”错误](https://support.microsoft.com/help/2887306)
- [“拒绝访问”错误](https://support.microsoft.com/help/2887685)
- [“用户名或密码不正确”错误](https://support.microsoft.com/help/2887705)

## 详细信息

有关适用于 Windows PowerShell 的 Azure Active Directory 模块的详细信息，请参阅 [使用 Windows PowerShell](/zh-cn/previous-versions/azure/jj151815(v=azure.100)) 管理Microsoft Entra ID。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/cannot-connect-cloud-services-powershell)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
