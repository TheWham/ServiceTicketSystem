# Windows 10 设备设置无法同步时出错：此用户无法登录，因为此帐户当前已禁用

本文介绍以下问题：Windows 10 设置无法同步时记录错误“事件 ID 6065：80070533 此用户无法登录，因为此帐户当前已禁用”。

*原始产品版本：* Windows 10 版本 1803、版本 1709、版本 1703、版本 1511、版本 1607、所有版本  
*原始 KB 数：* 3193791

## 现象

已在 Microsoft Entra 管理中心和某些 Windows 10 客户端上启用了 **企业状态漫游** 。 同步的任何支持设置（例如桌面后台或任务栏位置）都不会在同一用户的设备之间同步。

此外，事件 ID 6065 在 Microsoft-Windows-SettingSync/Debug 事件日志中记录：

> 日志名称：Microsoft-Windows-SettingSync/Debug  
> 源：Microsoft-Windows-SettingSync  
> 日期： <日期和时间>  
> 事件 ID 6065：  
> 任务类别：无  
> 级别： 错误  
> 关键字：用户： <用户 SID>  
> 计算机：WIN10DESKTOP  
> 说明：shell\roaming\cloudsync\cloudsyncengine\cloudsyncengine.cpp（990）\SettingSyncHost.exe！00007FF701A2A8C2： （调用方： 00007FF701A2A3D9） ReturnHr[PreRelease]（17） tid（1060） 80070533此用户无法登录，因为此帐户当前已禁用。 CallContext：[\AttemptSyncActivity]

## 原因

尚未使用 RMSBASIC 订阅预配租户。 在 Microsoft Entra 管理中心中启用企业状态漫游**并用于加密同步数据时**，会自动发生这种情况。 如果 `AllowAdHocSubscriptions` 租户设置为 **False** ，此配置可能会阻止使用 RMSBASIC 订阅预配租户。

注意

自 2024 年 3 月 30 日起，Azure AD 和 MSOnline PowerShell 模块已弃用。 若要了解详细信息，请阅读[有关弃用的更新](https://techcommunity.microsoft.com/t5/microsoft-entra-blog/important-azure-ad-graph-retirement-and-powershell-module/ba-p/3848270)。 在此日期之后，对这些模块的支持仅限于到 Microsoft Graph PowerShell SDK 的迁移帮助和安全性修复。 弃用的模块将持续运行至 2025 年 3 月 30 日。

我们建议迁移到 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview)，以便与 Microsoft Entra ID（以前称为 Azure AD）进行交互。 有关常见迁移问题，请参阅[迁移常见问题解答](/zh-cn/powershell/azure/active-directory/migration-faq)。
*注意：*2024 年 6 月 30 日之后，MSOnline 版本 1.0.x 可能会遇到中断。

## 解决方法

### 验证是否在租户上启用了 RMSBASIC 订阅

1. 打开 PowerShell 并使用 Microsoft Entra 凭据登录到 Microsoft Entra ID。 第一行将提示输入凭据。 第二行连接到 Microsoft Entra ID。

   ```
   $msolcred = get-credential connect-msolservice -credential $msolcred
   ```
2. 运行以下 cmdlet 以查看公司拥有的所有 SKU。

   ```
   Get-MsolAccountSku
   ```
3. 如果列出 RMSBASIC，如以下示例输出中所示，则无需继续执行本文的其余步骤。

   | AccountSkuId | ActiveUnits | WarningUnits | ConsumedUnits |
   | --- | --- | --- | --- |
   | --------------- | ------------ | --------------- | ----------------- |
   | tenantname：ENTERPRISEPACK | 25 | 0 | 14 |
   | tenantname：INTUNE\_A | 25 | 0 | 23 |
   | tenantname：AAD\_PREMIUM | 100 | 0 | 21 |
   | tenantname：RIGHTSMANAGEMENT\_ADHOC | 1000 | 0 | 18 |
   | tenantname： RMSBASIC | 1000 | 0 | 18 |
4. 如果 RMSBASIC 不存在，如以下示例输出所示，请继续执行下一部分中的步骤。

   | AccountSkuId | ActiveUnits | WarningUnits | ConsumedUnits |
   | --- | --- | --- | --- |
   | --------------- | ------------ | --------------- | ----------------- |
   | tenantname：ENTERPRISEPACK | 25 | 0 | 14 |
   | tenantname：INTUNE\_A | 25 | 0 | 23 |
   | tenantname：AAD\_PREMIUM | 100 | 0 | 21 |
   | tenantname：RIGHTSMANAGEMENT\_ADHOC | 1000 | 0 | 18 |

### 验证 AllowAdHocSubscriptions 是否在租户上设置为“True”

如果 `AllowAdHocSubscriptions` 租户设置为 **False** ，则无法使用 RMSBASIC 订阅进行预配。 使用以下步骤验证配置 `AllowAdHocSubscriptions` 并将其暂时设置为 **True** 以获取 RMSBASIC 订阅。

1. 打开 PowerShell 并使用 Microsoft Entra 凭据登录到 Microsoft Entra ID。 第一行将提示输入凭据。 第二行连接到 Microsoft Entra ID。

   ```
   $msolcred = get-credential connect-msolservice -credential $msolcred
   ```
2. 运行以下 cmdlet 以确定租户 `AllowAdHocSubscriptions` 是否已设置为 **True** 或 **False**。

   ```
   Get-MsolCompanyInformation | fl AllowAdHocSubscriptions
   ```
3. 如果 `AllowAdHocSubscriptions` 设置为 **True**，则无需继续执行其余步骤。 如果为 False，可以运行以下命令来启用 `AllowAdHocSubscriptions`。 可以在后面的步骤中将其重新设置为 **False** 。

   ```
   Set-MsolCompanySettings -AllowAdHocSubscriptions $true
   ```
4. 在 Microsoft Entra 管理中心中，禁用并重新启用 **企业状态漫游**。
   **请参阅租户**部分中的“验证用户是否可能同步设置和企业应用数据”。
5. `Get-MsolAccountSku`运行 cmdlet 以查看是否已添加 RMSBASIC 订阅：

   ```
   Get-MsolAccountSku
   ```

### 验证用户是否在租户上启用了同步设置和企业应用数据

获取 Premium Microsoft Entra 订阅后，请按照以下步骤启用 **企业状态漫游**：

1. 登录到 Azure 经典门户。
2. 在左侧，选择 **ACTIVE DIRECTORY**，然后选择要为其启用 **企业状态漫游**的目录。
3. 转到 **“配置** ”选项卡。
4. 向下滚动页面，查找 **“用户可以同步设置和企业应用数据**”，并验证 **是否选择了“所有** ”或 **“已选中** ”。
5. 如果 **已选择“所有** ”或 **“已** 选定”，请选择“无”、“保存”，然后使用原始 SG 选项返回到之前选择 **的 ALL** 或 **SELECTED** ，然后再次保存。 有关屏幕截图的参考，请参阅 [在 Microsoft Entra ID](/zh-cn/azure/active-directory/devices/enterprise-state-roaming-enable) 中启用企业状态漫游。

### （可选）将租户上的 AllowAdHocSubscriptions 设置为“False”

如果要将 AllowAdHocSubscriptions 设置回 False，在租户上预配 RMSBASIC 订阅后使用此 cmdlet：

```
Set-MsolCompanySettings -AllowAdHocSubscriptions $false
```

## 详细信息

- [Azure Active Directory PowerShell 模块](/zh-cn/powershell/module/MSOnline/?view=azureadps-1.0&redirectedfrom=msdn&preserve-view=true)
- [Get-MsolAccountsku](/zh-cn/powershell/module/msonline/get-msolaccountsku?view=azureadps-1.0&preserve-view=true)
- [Set-MsolCompanySettings](/zh-cn/powershell/module/msonline/set-msolcompanysettings?view=azureadps-1.0&preserve-view=true)
- [管理员如何控制为个人 RMS 创建的帐户](/zh-cn/azure/information-protection/rms-for-individuals)
- [50,000 个席位分配给 Office 365 组织中的 RIGHTSMANAGEMENT\_ADHOC SKU](https://support.microsoft.com/help/2925380)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/event-id-6065-user-cant-sign)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
