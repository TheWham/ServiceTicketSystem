# Microsoft Entra ID 中的联合用户可能需要登录两次才能提示进行 MFA

本文讨论Microsoft Entra ID 中的联合用户必须登录两次才能运行 MFA 的问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 4037806

## 现象

假设出现了下面这种情景：

- 你有一个Microsoft Entra 租户，用户通过 Active Directory 联合服务（AD FS）进行联合。
- 在此租户中，Azure MFA 服务器或第三方 MFA 提供程序部署在 AD FS 中。

在这种情况下，用户可能会被迫登录，方法是在提示用户进行多重身份验证（MFA）并完成登录之前两次提供用户名和密码。

## 原因

**如果 MsolDomainFederationSettings -SupportsMFA** 值设置为 **$true**，并且 **-PromptLoginBehavior** 值设置为 **TranslateToFreshPasswordAuth，Microsoft** Entra ID 会将 MFA 请求发送到标识提供者以进行分步身份验证。 Microsoft Entra ID 还会请求新的用户登录名。 这可以通过将以下参数发送到 AD FS 来实现：

`wauth=http://schemas.microsoft.com/claims/multipleauthn`  
`wfresh=0`

发生此情况时，无论用户是否刚刚登录，都会再次提示用户输入用户名和密码。 仅在用户第二次输入凭据后，才会提示用户输入 MFA。

## 解决方法

若要解决此问题，必须将 Microsoft Entra ID 配置为让 AD FS 通过将 **-PromptLoginBehavior** 设置更改为 **NativeSupport** 来本机处理此请求。 为此，请按照下列步骤进行操作：

重要

AD FS 部署必须在 Windows Server 2016 或 Windows Server 2012 R2 上运行，并且必须安装 2016 年 7 月更新 [KB 3172614](https://support.microsoft.com/help/4009451/windows-8-1-windows-server-2012-r2-update-kb3172614) 。

注意

自 2024 年 3 月 30 日起，Azure AD 和 MSOnline PowerShell 模块已弃用。 若要了解详细信息，请阅读[有关弃用的更新](https://techcommunity.microsoft.com/t5/microsoft-entra-blog/important-azure-ad-graph-retirement-and-powershell-module/ba-p/3848270)。 在此日期之后，对这些模块的支持仅限于到 Microsoft Graph PowerShell SDK 的迁移帮助和安全性修复。 弃用的模块将持续运行至 2025 年 3 月 30 日。

我们建议迁移到 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview)，以便与 Microsoft Entra ID（以前称为 Azure AD）进行交互。 有关常见迁移问题，请参阅[迁移常见问题解答](/zh-cn/powershell/azure/active-directory/migration-faq)。
*注意：*2024 年 6 月 30 日之后，MSOnline 版本 1.0.x 可能会遇到中断。

1. `Connect`运行以下命令登录到 Microsoft Entra ID 管理员帐户：

   ```
   Connect-Msolservice
   ```

   注意

   每次启动新会话时运行此命令。
2. 将 Microsoft Entra ID 配置为使用 **prompt=login** 行为运行联合用户身份验证。 这可以防止用户开始新的身份验证。 例如，运行以下命令，包括特定于租户的信息：

   ```
   Set-MsolDomainFederationSettings -DomainNameyour_domain_name-PreferredAuthenticationProtocol <current auth setting such as WsFed> -SupportsMfa $True -PromptLoginBehavior NativeSupport
   ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/federated-users-sign-in-two-times-mfa)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
