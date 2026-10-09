# 使用 Azure Active Directory 同步工具时，一个或多个对象未同步

## 概要

本文解决了一个或多个Active Directory 域服务（AD DS）对象属性无法通过 Azure Active Directory 同步工具同步到 Microsoft Entra ID 的问题。

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2643629

注意

本文有帮助吗? 你的输入对我们很重要。 请使用此页上的 **“反馈** ”按钮告诉我们本文为你工作得有多好，或者我们如何改进它。

## 现象

一个或多个 AD DS 对象或属性不会按预期同步Microsoft Entra ID。 当 Active Directory 同步运行时，对象不会同步，并且遇到以下症状之一：

- 你会收到一条错误消息，指出属性具有重复值。
- 你会收到一条错误消息，指出一个或多个属性违反格式要求，如字符集或字符长度。
- 你没有收到错误消息，目录同步似乎已完成。 但是，某些对象或属性不会按预期更新。

你可能会收到的错误消息的一些示例：

> Microsoft Online Services 目录中已存在具有相同代理地址的同步对象。

> 无法更新此对象，因为找不到用户 ID。

> 无法在 Microsoft Online Services 中更新此对象，因为与此对象关联的以下属性具有可能已与本地目录中另一个对象关联的值。

## 原因

此问题由以下原因之一导致：

- AD DS 属性使用的域值尚未验证。
- 需要唯一值的一个或多个对象属性在现有用户帐户中具有重复的属性值（例如 proxyAddresses 属性或 U serPrincipalName 属性）。
- 一个或多个对象属性违反了限制字符和属性值字符长度的格式要求。
- 一个或多个对象属性与目录同步的排除规则匹配。

  下表显示了默认同步范围规则：

  | 对象类型 | 属性名 | 同步失败时的属性条件 |
  | --- | --- | --- |
  | 联系人 | DisplayName | 包含“MSOL” |
  |  | msExchHideFromAddressLists | 设置为“True” |
  | 已启用安全性的组 | isCriticalSystemObject | 设置为“True” |
  | 已启用邮件的组 （安全组或通讯组列表） | proxyAddresses  和  邮件 | 没有“SMTP：”地址条目  和  不存在 |
  | 已启用邮件的联系人 | proxyAddresses  和  邮件 | 没有“SMTP：”地址条目  和  不存在 |
  | iNetOrgPerson | sAMAccountName | 不存在 |
  |  | isCriticalSystemObject | 存在 |
  | 用户 | mailNickname | 以“SystemMailbox”开头 |
  |  | mailNickname | 以“CAS\_”开头  和  包含“}” |
  |  | sAMAccountName | 以“CAS\_”开头  和  包含“}” |
  |  | sAMAccountName | 等于“SUPPORT\_388945a0” |
  |  | sAMAccountName | 等于“MSOL\_AD\_Sync” |
  |  | sAMAccountName | 不存在 |
  |  | isCriticalSystemObject | 设置为“True” |
- 初始同步后，用户主体名称（UPN）已更改，必须手动更新。
- 同步用户的 Exchange Online 简单邮件传输协议 （SMTP） 地址不会在本地 Active Directory架构中正确填充。

## 解决方法

若要解决此问题，请根据需要使用以下方法之一。

### 运行 IdFix 以检查重复项、缺少属性和规则冲突

[使用 IdFix DirSync 错误修正工具](https://github.com/microsoft/idfix)查找阻止同步Microsoft Entra ID 的对象和错误。

- 如果在运行 IdFix 后在 ERROR **列中看到“空白”**，则不会定义对象的 displayName 属性。 若要解决此问题，请使用以下步骤为对象的 displayName 属性指定值：

1. 在对象的 UPDATE 列中，键入其 displayName 属性的名称。
2. 在 ACTION 列中，单击“编辑”，然后单击“应用”。
3. 对 ERROR 列中具有“空白”条目的每个对象重复步骤 1 和步骤 2。
4. 再次运行 IdFix 以查找更多对象错误。

- 如果在运行 IdFix 后在 ERROR **列中看到“重复”**，则两个或多个对象具有相同的电子邮件地址。 若要解决此问题，请使用以下步骤为对象指定唯一的电子邮件地址：

1. 在对象的 UPDATE 列中，键入尚未使用的电子邮件地址。
2. 在 ACTION 列中，单击“编辑”，然后单击“应用”。
3. 再次运行 IdFix 以查找更多对象错误。

### 确定由未通过目录同步在 Microsoft Entra ID 中创建的对象引起的属性冲突

若要确定由使用管理工具创建的用户对象引起的属性冲突（并且未通过目录同步在 Microsoft Entra ID 中创建），请执行以下步骤：

1. 确定本地 AD DS 用户帐户的唯一属性。 为此，在安装了 Windows 支持工具的计算机上，请执行以下步骤：

   1. 选择“开始”，选择**“运行**”**，键入ldp.exe，然后选择“**确定**”。**
   2. 选择“连接”，选择**“连接”，键入 AD DS 域控制器的计算机名称，然后选择“**确定**”。**
   3. 选择“ **连接**”，选择“ **绑定**”，然后选择“ **确定**”。
   4. 依次选择“视图”、“树视图**”、“BaseDN**”下拉列表中的** AD DS 域，然后选择“**确定**”。**
   5. 在导航窗格中，找到并双击未正确同步的对象。 窗口右侧的“详细信息”窗格列出了所有对象属性。 以下示例显示了对象属性：

      ![列出所有对象属性的 Windows 支持工具导航和详细信息窗格的屏幕截图。](media/objects-dont-sync-ad-sync-tool/object-attributes.png)
   6. 记录多值 proxyAddresses 属性中的 userPrincipalName 属性和每个 SMTP 地址的值。 在后面的步骤中会用到这些值。

      | 属性名 | 示例 | 备注 |
      | --- | --- | --- |
      | proxyAddresses | proxyAddresses （3）： x500：/o=Exchange/ou=Exchange 管理组 （FYDIBOHF23SPDLT）/cn=Recipients/cn=1ae75fca0d3a4303802cea9ca50fcd4f-7628376;smtp：`7628376@service.contoso.com`;SMTP：`7628376@contoso.com`; | 1. 属性标签旁的括号中显示的数字指示多值属性中的代理地址值数。   2.每个不同的代理地址值都由分号（;)）指示。  3.主 SMTP 代理地址值由大写“SMTP：”指示 |
      | userPrincipalName | `7628376@contoso.com` |  |

      注意

      Ldp.exe包含在 Windows Server 2008 和 Windows Server 2003 支持工具中。 Windows Server 2003 支持工具包含在 Windows Server 2003 安装介质中。 或者，若要获取支持工具，请转到以下Microsoft网站： [Windows Server 2003 Service Pack 2 32 位支持工具](https://go.microsoft.com/fwlink/?linkid=100114)
2. 使用适用于 Windows PowerShell 的 Azure Active Directory 模块连接到 Microsoft Entra ID。 有关详细信息，请转到 [使用 Windows PowerShell](/zh-cn/previous-versions/azure/jj151815(v=azure.100)?redirectedfrom=MSDN) 管理Microsoft Entra ID。

   使控制台窗口保持打开状态。 在下一步中，需要使用它。
3. 检查是否存在重复的 userPrincipalName 属性。

   在步骤 2 中打开的控制台连接中，按照显示命令的顺序键入以下命令。 在每个命令后按 Enter：

   ```
   $userUPN = "<search UPN>"
   ```

   注意

   在此命令中，占位符“<搜索 UPN>”表示在步骤 1f 中记录的 UserPrincipalName 属性。

   ```
   Get-MSOLUser -UserPrincipalName $userUPN | where {$_.LastDirSyncTime -eq $null}
   ```

   注意

   自 2024 年 3 月 30 日起，Azure AD 和 MSOnline PowerShell 模块已弃用。 若要了解详细信息，请阅读[有关弃用的更新](https://techcommunity.microsoft.com/t5/microsoft-entra-blog/important-azure-ad-graph-retirement-and-powershell-module/ba-p/3848270)。 在此日期之后，对这些模块的支持仅限于到 Microsoft Graph PowerShell SDK 的迁移帮助和安全性修复。 弃用的模块将持续运行至 2025 年 3 月 30 日。

   我们建议迁移到 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview)，以便与 Microsoft Entra ID（以前称为 Azure AD）进行交互。 有关常见迁移问题，请参阅[迁移常见问题解答](/zh-cn/powershell/azure/active-directory/migration-faq)。
   *注意：*2024 年 6 月 30 日之后，MSOnline 版本 1.0.x 可能会遇到中断。

   使控制台窗口保持打开状态。 在下一步中，你将再次使用它。
4. 检查是否存在重复的 proxyAddresses 属性。 在步骤 2 中打开的控制台连接中，运行以下命令：

   ```
   Import-Module ExchangeOnlineManagement
   ```
5. 对于在步骤 1f 中记录的每个代理地址条目，键入以下命令的顺序显示它们。 在每个命令后按 Enter：

   ```
   $proxyAddress = "<search proxyAddress>"
   ```

   注意

   在此命令中，占位符“<search proxyAddress>”表示在步骤 1f 中记录的 proxyAddresses 属性的值。

   ```
   Get-EXOMailbox | where {[string] $str = ($_.EmailAddresses); $str.tolower().Contains($proxyAddress.tolower()) -eq $true} | foreach {get-MSOLUser -UserPrincipalName $_.MicrosoftOnlineServicesID | where {($_.LastDirSyncTime -eq $null)}}
   ```

在步骤 3 和 4 中运行命令后返回的项表示未通过目录同步创建的用户对象，并且具有与未正确同步的对象冲突的属性。

### 更新 AD DS 属性以删除重复项、规则冲突和范围排除项

根据以下信息确定阻止同步的特定属性：

- 管理电子邮件
- Office 365 部署就绪情况工具输出中的报表
- 默认目录同步范围规则和自定义规则

识别特定属性值后，使用以下方法之一编辑属性值：

- 使用Active Directory 用户和计算机工具编辑属性值。

1. 打开Active Directory 用户和计算机，然后选择 AD DS 域的根节点。
2. 选择“视图” **，** 并确保 **已选择“高级功能** ”选项。
3. 在左侧导航窗格中，找到用户对象，右键单击该对象，然后选择“ **属性**”。
4. 在 **“对象编辑器** ”选项卡上，找到所需的属性。 选择“编辑”，然后将属性值编辑为所需的值。
5. 选择两次“确定”。

- 使用 Active Directory 服务接口 （ADSI） 编辑更新 AD DS 中的对象属性。
  你可以下载并安装 ADSI Edit 作为 Windows Server 工具包的一部分。 若要使用 ADSI 编辑编辑属性，请执行以下步骤。

警告

此过程需要 ADSI 编辑。 错误地使用 ADSI 编辑可能会导致严重问题，这些问题可能需要重新安装操作系统。 Microsoft无法保证可以解决使用 ADSI 编辑错误导致的问题。 以自己的风险使用 ADSI 编辑。

1. 选择“开始”，选择**“运行”，键入 ADSIEdit.msc，然后选择“**确定**”。**
2. 在**导航窗格中右键单击 ADSI 编辑**，选择“**连接到**”，然后选择“确定**”**加载域分区。
3. 找到用户对象，右键单击该对象，然后选择“ **属性**”。
4. 在 **“属性”** 列表中，找到所需的属性。 选择“编辑”，然后将属性值编辑为所需的值。
5. 选择 **“确定** ”两次，然后退出 ADSI 编辑。

### 创建新组并将其添加到未同步的内置组

若要解决某些内置组（如域用户组）未同步的问题，请创建一个新组，其中包含内置组的所有适用成员和适当的权限。 然后，将该组添加为未同步的内置组的成员。 使用新组而不是内置组来管理成员。 通过使用此方法，仍只管理一个组。

你不希望更改内置组的属性或更改标识同步设备的范围规则，以允许同步关键系统对象。 它可能会触发其他意外行为。

### 使用 SMTP 匹配导致本地用户对象同步到现有用户对象

有关详细信息，请参阅 [如何使用 SMTP 匹配将本地用户帐户与 Office 365 用户帐户匹配，以便进行目录同步](https://support.microsoft.com/help/2641663)。

### 手动更新用户帐户 UPN

若要更新在初始目录同步后获得许可的用户帐户 UPN，请执行以下步骤：

1. 安装 Azure Active Directory v2 PowerShell 模块。 有关详细信息，请参阅 [Azure Active Directory v2 PowerShell 模块](https://www.powershellgallery.com/packages/AzureAD/2.0.0.71)。
2. 在 Azure Active Directory v2 PowerShell 提示符下运行以下 cmdlet：

   ```
   $cred = get-credential
   ```

   注意

   出现提示时，输入管理员凭据。

   ```
   Connect-AzureAD
   ```

   ```
   Set-AzureADUser -ObjectId [CurrentUPN] -UserPrincipalName [NewUPN]
   ```

### 使用本地 Active Directory属性更新用户 SMTP 地址

如果 SMTP 属性未按预期方式同步到 Exchange Online，可能需要更新本地 Active Directory属性。 若要更新本地 Active Directory属性，以便正确的电子邮件地址显示在 Exchange Online 中，请使用解决方法 2 来操作下表中的属性。

| 本地 Active Directory 属性名称 | 本地 Active Directory 属性值示例 | Exchange Online 电子邮件地址示例 |
| --- | --- | --- |
| proxyAddresses | SMTP：`user1@contoso.com` | 主 SMTP： `user1@contoso.com` 辅助 SMTP： `user1@contoso.onmicrosoft.com` |
| proxyAddresses | smtp：`user1@contoso.com` | 主 SMTP： `user1@contoso.onmicrosoft.com` 辅助 SMTP： `user1@contoso.com` |
| proxyAddresses | SMTP：`user1@contoso.com` smtp：`user1@sub.contoso.com` | 主 SMTP： `user1@contoso.com` 辅助 SMTP： `user1@sub.contoso.com` 辅助 SMTP： `user1@contoso.onmicrosoft.com` |
| 邮件 | `User1@contoso.com` | 主 SMTP： `user1@contoso.com` 辅助 SMTP： `user1@contoso.onmicrosoft.com` |
| UserPrincipalName | `User1@contoso.com` | 主 SMTP： `user1@contoso.com` 辅助 SMTP： `user1@contoso.onmicrosoft.com` |

与默认域（例如 `user1@contoso.onmicrosoft.com`）关联的Microsoft联机电子邮件路由地址（MOERA）条目是基于用户帐户别名的解释值。 此特殊电子邮件地址与每个 Exchange Online 收件人密不可分地链接。 无法管理、删除或为任何收件人创建其他 MOERA 地址。 但是，MOERA 地址可以使用本地 Active Directory用户对象中的属性作为主 SMTP 地址进行过度覆盖。

注意

proxyAddresses 属性中的数据的存在完全掩盖 Exchange Online 电子邮件地址填充的邮件属性中的数据。

注意

proxyAddresses 属性、邮件属性或这两个属性中的数据都完全屏蔽了 Exchange Online 电子邮件地址填充的 UserPrincipalName 数据。 UPN 可用于管理电子邮件地址。 但是，管理员可以决定通过填充 proxyAddresses 或邮件属性单独管理电子邮件地址和 UPN。

强烈建议一致地使用这些属性之一来管理同步用户的 Exchange Online 电子邮件地址。

## 详细信息

本文中提到的 Windows PowerShell 命令需要适用于 Windows PowerShell 的 Azure Active Directory 模块。 有关适用于 Windows PowerShell 的 Azure Active Directory 模块的详细信息，请参阅以下文章：  
[使用 Windows PowerShell](/zh-cn/previous-versions/azure/jj151815(v=azure.100)?redirectedfrom=MSDN) 管理Microsoft Entra ID。

有关按属性筛选目录同步的详细信息，请参阅以下 Microsoft TechNet wiki 文章：  
[Azure Active Directory 同步工具同步的属性列表](/zh-cn/archive/technet-wiki/19901.dirsync-list-of-attributes-that-are-synced-by-the-azure-active-directory-sync-tool)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/objects-dont-sync-ad-sync-tool)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
