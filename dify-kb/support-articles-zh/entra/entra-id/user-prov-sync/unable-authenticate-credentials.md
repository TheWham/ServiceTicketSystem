# 尝试连接到 Microsoft Entra ID 时出现“无法对凭据进行身份验证”错误

## 概要

本文提供有关在尝试连接到 Microsoft Entra ID 时解决“无法对凭据进行身份验证”错误的指南。

*原始产品版本：*Microsoft Entra ID、云服务（Web 角色/辅助角色）、Microsoft Intune、Azure 备份、Office 365 用户和域管理、Office 365 标识管理  
*原始 KB 数：* 2929554

## 现象

尝试使用适用于 Windows PowerShell 的 Azure Active Directory 模块连接到 Microsoft Entra ID 时，会收到以下错误消息：

```
Connect-MsolService : Unable to authenticate your credentials. Make sure that
your user name is in the format: <username>@<domain>. If this issue persists,
contact Support.

At line:1 char:1
+ Connect-MsolService
+ ~~~~~~~~~~~~~~~~~~~
+ CategoryInfo : OperationStopped: (:) [Connect-MsolService], Mic
rosoftOnlineException
+ FullyQualifiedErrorId : 0x80048862,Microsoft.Online.Administration.Autom
ation.ConnectMsolService
```

注意

自 2024 年 3 月 30 日起，Azure AD 和 MSOnline PowerShell 模块已弃用。 若要了解详细信息，请阅读[有关弃用的更新](https://techcommunity.microsoft.com/t5/microsoft-entra-blog/important-azure-ad-graph-retirement-and-powershell-module/ba-p/3848270)。 在此日期之后，对这些模块的支持仅限于到 Microsoft Graph PowerShell SDK 的迁移帮助和安全性修复。 弃用的模块将持续运行至 2025 年 3 月 30 日。

我们建议迁移到 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview)，以便与 Microsoft Entra ID（以前称为 Azure AD）进行交互。 有关常见迁移问题，请参阅[迁移常见问题解答](/zh-cn/powershell/azure/active-directory/migration-faq)。
*注意：*2024 年 6 月 30 日之后，MSOnline 版本 1.0.x 可能会遇到中断。

## 原因

如果满足以下条件之一，则会出现此问题：

- 输入用户名时使用了不正确的格式。
- 用户帐户已启用 Microsoft Entra 多重身份验证。

## 解决方法

根据需要执行以下操作之一。

### 方案 1：输入用户名时使用了不正确的格式

输入用户名时使用以下格式：

`<user_name >@<domain>`

例如， `john@contoso.com` 格式正确。 输入 `john` 或 `contoso\john` 不起作用。

### 方案 2：用户帐户已启用Microsoft Entra 多重身份验证

如果用户帐户已启用 Microsoft Entra 多重身份验证，Microsoft当前不支持使用适用于 Windows PowerShell 的 Azure Active Directory 模块连接到 Microsoft Entra ID。

若要使用适用于 Windows PowerShell 的 Azure Active Directory 模块执行管理任务，请使用以下任一方法：

- 为用户帐户禁用Microsoft Entra 多重身份验证。
- 使用未为 Microsoft Entra 多重身份验证启用的其他管理员帐户。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/unable-authenticate-credentials)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
