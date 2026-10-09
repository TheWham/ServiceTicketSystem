# Microsoft Entra ID 中的联合用户被迫频繁登录

本文讨论Microsoft Entra ID 中的联合用户被迫频繁登录的问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 4025960

## 现象

在联合用户登录到 Microsoft Entra ID 后，他们被迫持续重新登录，而不是保持登录状态。

## 原因

将向未同步 LastPasswordChangeTimestamp 属性的联合用户颁发最大期限值为 12 小时的会话 Cookie 和刷新令牌。 这意味着程序可以静默检索新令牌，使用户的会话仅保持活动状态长达 12 小时。 之后，用户将返回到原始 IdP 以重新进行身份验证。

之所以发生这种情况，是因为Microsoft Entra ID 无法确定何时撤销与旧凭据相关的令牌（例如已更改的密码）。 因此，Microsoft Entra ID 必须更频繁地检查，以确保用户和关联的令牌仍然处于良好地位。
有关令牌生存期及其管理方式的详细信息，请参阅以下Microsoft Azure 文章：

[Microsoft Entra ID（公共预览版）中的可配置令牌生存期](/zh-cn/azure/active-directory/active-directory-configurable-token-lifetimes)

## 解决方法

若要解决此问题，租户管理员必须确保同步 **LastPasswordChangeTimestamp** 属性。 同步此属性可改善用户体验和安全状态。

可以使用 PowerShell 或通过 Microsoft Entra Connect 对用户对象进行此设置。

### PowerShell

可以使用 Azure AD PowerShell V1 （MSOnline） 模块为用户设置 **StsRefreshTokensValidFrom** 属性。 这将通知 Microsoft Entra 身份验证流，以便根据Microsoft Entra 策略为用户提供更长的持久刷新令牌或刷新令牌。 为此，请按照下列步骤进行操作：

注意

自 2024 年 3 月 30 日起，Azure AD 和 MSOnline PowerShell 模块已弃用。 若要了解详细信息，请阅读[有关弃用的更新](https://techcommunity.microsoft.com/t5/microsoft-entra-blog/important-azure-ad-graph-retirement-and-powershell-module/ba-p/3848270)。 在此日期之后，对这些模块的支持仅限于到 Microsoft Graph PowerShell SDK 的迁移帮助和安全性修复。 弃用的模块将持续运行至 2025 年 3 月 30 日。

我们建议迁移到 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview)，以便与 Microsoft Entra ID（以前称为 Azure AD）进行交互。 有关常见迁移问题，请参阅[迁移常见问题解答](/zh-cn/powershell/azure/active-directory/migration-faq)。
*注意：*2024 年 6 月 30 日之后，MSOnline 版本 1.0.x 可能会遇到中断。

1. 下载最新的 Azure AD PowerShell V1 版本。
2. **运行 Connect** 命令，在每次启动新会话时登录到 Microsoft Entra 管理员帐户：

   ```
   Connect-msolservice
   ```
3. **使用以下命令设置 StsRefreshTokensValidFrom** 属性：

   ```
   $RefreshTokensValidFrom = Get-Date
   Set-MsolUser -UserPrincipalName<UPN of user>-StsRefreshTokensValidFrom $RefreshTokensValidFrom
   ```

   例如：

   ```
   $RefreshTokensValidFrom = Get-Date
   Set-MsolUser -UserPrincipalName john@contoso.com -StsRefreshTokensValidFrom $RefreshTokensValidFrom
   ```

   注意

   StsRefreshTokenValidFromwill 似乎接受任何日期，但它将始终设置为当前日期和时间。
4. 有关更多帮助，请联系 [Azure 支持部门](https://azure.microsoft.com/support/options/)。

### Microsoft Entra Connect

Microsoft Entra Connect 默认同步此属性。 但是，Microsoft Entra Connect 可以通过使用 [属性筛选功能](/zh-cn/azure/active-directory/connect/active-directory-aadconnect-get-started-custom#azure-ad-app-and-attribute-filtering) 或禁用现用同步规则来同步或不同步此属性。

#### 使用 Microsoft Entra 应用和属性筛选功能

如果以前已使用 Microsoft Entra 应用和属性筛选功能禁用了 PwdLastSet **属性的**同步，请执行以下步骤重新启用该过程：

#### 禁用现用同步规则

1. 登录到 Microsoft Entra Connect 服务器，然后启动 Microsoft Entra Connect 向导。
2. 单击“ **自定义同步选项”任务**。
3. 导航到 **“可选功能** ”屏幕，并验证是否已启用Microsoft Entra 应用和属性筛选功能。 否则，这意味着该功能尚未用于禁用 PwdLastSet **属性的**同步。
4. 导航到 **“Microsoft Entra 属性”** 屏幕，并启用 **PwdLastSet** 属性。 如果已启用此功能，则意味着该功能尚未用于禁用 PwdLastSet **属性的**同步。
5. 完成向导，然后保存配置。
6. 通过在 PowerShell 中运行以下 cmdlet 来运行完全同步周期：

   ```
   Start-ADSyncSyncCycle -policyType initial
   ```

   注意

   如果Microsoft Entra 应用和属性筛选功能已禁用（请参阅步骤 3），或者 **已启用 PwdLastSet** 属性（请参阅步骤 4），这意味着该功能尚未用于禁用 **PwdLastSet** 属性。 在这种情况下，可以跳过步骤 5 和 6。

Microsoft Entra Connect 使用以下现用同步规则实现 PwdLastSet **属性的**同步。

| 现用同步规则 | 详细信息 |
| --- | --- |
| 从 Active Directory 导入 | 用户通用将本地 AD **PwdLastSet** 属性导入到 Metaverse **PwdLastSet** 属性。 |
| Microsoft条目 ID | 用户加入导出 Metaverse PwdLastSet 属性到 Microsoft Entra ID **LastPasswordChangeTimestamp** 属性。 |

在以下屏幕截图中，可以看到如何使用 Microsoft Entra Connect 同步规则编辑器在两个同步规则中实现属性流。

![Microsoft Entra Connect 同步规则编辑器的屏幕截图。](media/federated-users-forced-sign-in/synchronization-rules.png)

客户可以通过禁用这些现成同步规则并将其替换为自定义同步规则来禁用 **PwdLastSet** 属性的同步。 若要启用 PwdLastSet **属性的**同步，请考虑重新启用这些现式同步规则或在现有自定义同步规则中实现相同的属性流。

有关如何实现和验证同步规则更改的详细信息，请参阅文章 [Microsoft Entra Connect Sync：如何更改默认配置](/zh-cn/entra/identity/hybrid/connect/how-to-connect-sync-change-the-configuration)。

#### 密码哈希同步

如果在 Microsoft Entra Connect 上启用了密码哈希同步功能，则密码同步管理器会将 本地 Active Directory **PwdLastSet** 属性与 Microsoft Entra ID **LastPasswordChangeTimestamp** 属性同步。 即使 **PwdLastSet** 属性已使用此部分中的两种方法进行筛选，也是如此。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/federated-users-forced-sign-in)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
