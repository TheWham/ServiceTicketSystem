# 身份验证失败，并出现错误，指出“请求的联合领域对象 '< 对象 ID >' 不存在”

身份验证失败，错误为“请求的联合领域对象'<对象 ID >'不存在”，这些用户属于域的一部分，该域与Microsoft Entra ID [或](https://www.microsoft.com/microsoft-365) [Microsoft 365](https://azure.microsoft.com/services/active-directory/) 中的第三方标识提供者联合。

![登录到联合域时出错的屏幕截图。](media/authentication-fails-with-error/authentication-fails-trouble-sign-in.png)

![错误的故障排除详细信息的屏幕截图。](media/authentication-fails-with-error/troubleshooting-details.png)

当第三方标识提供者在安全断言标记语言（SAML）响应的*颁发者*字段中返回错误的 **IssuerURI** 时，会发生此失败。

## 解决方法 1

请联系第三方标识提供者的支持团队，并在 SAML 中更正作为 *颁发者*返回的 IssuerURI，并通过客户端返回到 Microsoft Entra ID 或Microsoft 365。

## 解决方法 2

使用命令 `Set-MsolDomainFederationSettings` 修改联合域的 IssuerURI 以匹配错误中列出的域对象。

注意

自 2024 年 3 月 30 日起，Azure AD 和 MSOnline PowerShell 模块已弃用。 若要了解详细信息，请阅读[有关弃用的更新](https://techcommunity.microsoft.com/t5/microsoft-entra-blog/important-azure-ad-graph-retirement-and-powershell-module/ba-p/3848270)。 在此日期之后，对这些模块的支持仅限于到 Microsoft Graph PowerShell SDK 的迁移帮助和安全性修复。 弃用的模块将持续运行至 2025 年 3 月 30 日。

我们建议迁移到 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview)，以便与 Microsoft Entra ID（以前称为 Azure AD）进行交互。 有关常见迁移问题，请参阅[迁移常见问题解答](/zh-cn/powershell/azure/active-directory/migration-faq)。
*注意：*2024 年 6 月 30 日之后，MSOnline 版本 1.0.x 可能会遇到中断。

1. 使用 *MSONLINE* 模块连接到 Microsoft Entra ID。 要检查模块是否已安装，请打开 PowerShell 并执行 `get-module MSONLINE -ListAvailable` 命令。
2. 按照安装 Azure AD 模块[中所述](/zh-cn/powershell/azure/active-directory/install-msonlinev1#install-the-azure-ad-module)的步骤安装模块。
3. 运行以下命令以验证联合域的首选身份验证协议。

   ```
   $federationSettings=Get-MsolDomainFederationSettings -DomainName domain.com

   $federationSettings.PreferredAuthenticationProtocol
   ```
4. 如果`PreferredAuthenticationProtocol`步骤 3 中列出的值显示为 **WSFED**，请运行以下命令以更新 **IssuerURI**。

   ```
   Set-MsolDomainFederationSettings -DomainName domain.com -IssuerUri "value of federated realm object listed in the authentication failure message"
   ```

   身份验证失败消息中Microsoft Entra ID 列出了必要的 IssuerURI 值。
5. 如果`PreferredAuthenticationProtocol`步骤 3 中列出的值为 SAMLP（SAML 协议），运行以下命令更新 IssuerURI。

   ```
   Set-MsolDomainFederationSettings -DomainName domain.com -IssuerUri "value of federated realm object listed in the authentication failure message" -PreferredAuthenticationProtocol samlp
   ```

   身份验证失败消息中Microsoft Entra ID 列出了必要的 IssuerURI 值。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/authentication-fails-with-error)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
