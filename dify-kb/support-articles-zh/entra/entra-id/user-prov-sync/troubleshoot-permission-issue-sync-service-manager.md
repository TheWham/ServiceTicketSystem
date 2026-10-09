# 权限问题错误 8344，“访问权限不足，无法执行操作。”

## 总结

本文介绍如何理解和排查 "权限问题 [8344]" 错误，即 "权限不足，无法执行操作"。此 Microsoft Entra 错误发生在 Microsoft 同步服务管理器中，当本地 Active Directory 连接器执行导出操作时出现。

备注

本文有帮助吗? 你的输入对我们很重要。 请使用此页上的 **“反馈** ”按钮告诉我们本文为你工作得有多好，或者我们如何改进它。

## 症状

在 [**操作**选项卡](/zh-cn/azure/active-directory/hybrid/connect/how-to-connect-sync-service-manager-ui-operations)的 [Synchronization Service Manager](/zh-cn/azure/active-directory/hybrid/connect/how-to-connect-sync-service-manager-ui) 应用中，**“连接操作”** 表包含有一行，该行代表一个本地 AD 连接器，其中 **配置文件名称** 列的值为 **“导出”**。 但是，相应的**状态**列值是**完成-导出-错误**。 选择此表行时，辅助表会显示一个或多个 **权限问题** 导出错误。

[![Synchronization Service Manager 应用中权限问题错误的屏幕截图。](media/troubleshoot-permission-issue-sync-service-manager/sync-service-manager-symptoms.png)](media/troubleshoot-permission-issue-sync-service-manager/sync-service-manager-symptoms.png#lightbox)

如果选择一个 **权限问题的导出错误**，将会显示 **连接器空间对象属性** 对话框。 在“ **导出错误** ”选项卡上，将显示以下信息。

| “错误信息”字段 | 值 |
| --- | --- |
| **错误** | 权限问题 |
| **连接的数据源错误代码** | 8344 |
| **连接数据源错误** | 访问权限不足，无法执行操作。 |

[![同步服务管理器应用的“连接器空间对象属性”对话框中“导出错误”选项卡的屏幕截图。](media/troubleshoot-permission-issue-sync-service-manager/sync-service-manager-export-error.png)](media/troubleshoot-permission-issue-sync-service-manager/sync-service-manager-export-error.png#lightbox)

## 原因

本地 Active Directory连接器帐户 （`MSOL_<hex-digits>`） 在 Active Directory 中没有权限写回要与 Microsoft Entra ID 同步的对象的属性。

## 解决方案 1：使用 Microsoft Entra Connect 故障排除控制台授予权限

备注

将此解决方案用作推荐的首选方法。

在本地 Active Directory 连接器帐户（`MSOL_<hex-digits>`）中，找到此帐户没有权限的属性。 然后，使用 Microsoft Entra Connect 向导授予Microsoft Entra Connect 故障排除控制台中的权限，如以下部分所述。

### 第 1 部分：确定正在使用哪个本地 Active Directory连接器帐户

若要查找本地 AD 连接器帐户，请使用以下工具之一。

Microsoft Entra Connect 向导

1. 在 Windows 桌面上，双击 **Microsoft Entra Connect** 图标打开Microsoft Entra Connect 向导。
2. 在 **“Microsoft Entra Connect** ”对话框中，选择“ **配置** ”按钮。
3. 在 **“其他任务** ”屏幕中，选择 **“查看”或“导出当前配置** 任务”，然后选择“ **下一步** ”按钮。
4. 在**“查看解决方案**”屏幕中，找到**“同步目录”**标题，然后从 ACCOUNT **字段值内**复制字符串。 默认情况下，自动创建的帐户遵循格式 `DOMAIN\MSOL_<hex-digits>`。
5. **选择“退出**”按钮。

Synchronization Service Manager 应用

1. 选择“开始”，然后搜索并选择“**同步服务管理器**”。
2. 在 **Synchronization Service Manager** 应用中，选择“ **连接器** ”选项卡。
3. 在**“**连接器”列表中，右键单击本地 Active Directory连接器的名称值，然后选择“**属性**”。
4. 在 **“属性** ”对话框中，找到 **“连接器设计器** ”窗格，然后选择“ **连接到 Active Directory 林**”。
5. 在**“连接到 Active Directory 林”**窗格中，复制**“用户名”**字段的值。 此值包含本地 Active Directory连接器帐户的名称。

PowerShell 中的 ADSyncTools 模块

[如果 PowerShell 环境中尚未安装 ADSyncTools 模块](https://www.powershellgallery.com/packages/ADSyncTools)，请安装该模块。 安装模块后，运行 `Get-ADSyncToolsADconnectorAccount` cmdlet：

```
Install-Module ADSyncTools  # Not required if the ADSyncTools module is already installed
Get-ADSyncToolsADconnectorAccount
```

输出是一个表，显示每个 Active Directory 连接器帐户的 `Name`、`Forest`、`Domain` 和 `Username` 列。 要复制的文本字符串位于 `Username` 列中。

```
Name             Forest            Domain                 Username
----             ------            ------                 --------
corp.contoso.com corp.contoso.com  domain.contoso.com     MSOL__<hex-digits>
test.local       test.local        test.local             MSOL__<hex-digits>
```

### 第 2 部分：确定本地 Active Directory连接器帐户没有权限的属性

1. 选择“开始”，然后搜索并选择“**同步服务管理器**”。
2. 在 **Synchronization Service Manager** 应用中，选择 **操作** 选项卡。
3. 在 **“连接器作** ”表中，选择具有以下特征的行。

   | 列名 | 值 |
   | --- | --- |
   | **Name** | 本地 Active Directory 连接器的名称 |
   | **个人资料名称** | **导出** |
   | **状态** | **已完成的导出错误** |
4. 在右下表中，在第一列（标记为 **“导出错误**”）中选择一个对象，其中 **权限问题** 被列为第二列中的错误之一。
5. 在“**连接器空间对象属性**”对话框中，选择“**挂起的导出**”选项卡。
6. **找到“属性信息**”表，然后选择**“更改**”列以按该列排序。

   [![“属性信息”表的屏幕截图，“挂起的导出”选项卡，“连接器空间对象属性”对话框，“同步服务管理器”应用。](media/troubleshoot-permission-issue-sync-service-manager/pending-export-attribute-information.png)](media/troubleshoot-permission-issue-sync-service-manager/pending-export-attribute-information.png#lightbox)
7. 使用以下方法之一确定正在使用的 Microsoft Entra Connect 功能：

   - 使用 `mS-DS-ConsistencyGuid` 属性作为源定位点时，添加的属性是 [mS-DS-ConsistencyGuid](/zh-cn/entra/identity/hybrid/connect/plan-connect-design-concepts#using-ms-ds-consistencyguid-as-sourceanchor) 属性。
   - 查看要同步的 [Exchange 混合写回](/zh-cn/azure/active-directory/hybrid/connect/reference-connect-sync-attributes-synchronized#exchange-hybrid-writeback) 属性列表，然后返回到 **属性信息** 表 UI，查找 ADSync 尝试添加或修改的 Exchange 混合写回属性。 例如，添加或修改的属性可能是 [msDS-ExternalDirectoryObjectID](/zh-cn/openspecs/windows_protocols/ms-ada2/0abc1d06-ac09-476f-a60b-5deb05b394f7) 属性。
   - 通过从 PowerShell 会话运行 `Get-ADSyncGlobalSettings` cmdlet 来检查Microsoft Entra Connect 功能，如以下代码所示：

     ```
     (Get-ADSyncGlobalSettings).Parameters | select Name, Value | sort Name
     ```

### 第 3 部分：授予缺少的权限

重要

用于运行 Microsoft Entra Connect 工具的帐户必须有权向 Active Directory 授予所有域的权限。 通常，只有企业管理员对 Active Directory 林中的所有域具有域管理员权限。

1. 在 Windows 桌面上，双击 **Microsoft Entra Connect** 图标。
2. 在 **“Microsoft Entra Connect** ”对话框中，选择“ **配置** ”按钮。
3. 在 **“其他任务** ”窗格中，选择“ **故障排除** ”任务，然后选择“ **下一步** ”按钮。
4. 在 **“欢迎Microsoft Entra Connect 故障排除** ”页上，选择“ **启动** ”按钮以在控制台中启动故障排除菜单。
5. 在控制台的`AADConnect Troubleshooting`菜单中，输入 *4* 以配置Active Directory 域服务（AD DS）连接器帐户权限。

   ```
   ----------------------------------------AADConnect Troubleshooting-----------------------------------------

           Enter '1' - Troubleshoot Object Synchronization
           Enter '2' - Troubleshoot Password Hash Synchronization
           Enter '3' - Collect General Diagnostics
           Enter '4' - Configure AD DS Connector Account Permissions
           Enter '5' - Test Azure Active Directory Connectivity
           Enter '6' - Test Active Directory Connectivity
           Enter 'Q' - Quit

           Please make a selection: 4_
   ```
6. 在 `Configure Permissions` 菜单中，输入感兴趣的选项。 在此示例中，输入 *4* 以设置 Exchange 混合权限。

   ```
   --------------------------------------------Configure Permissions------------------------------------------

           Enter '1' - Get AD Connector account
           Enter '2' - Get objects with inheritance disabled
           Enter '3' - Set basic read permissions
           Enter '4' - Set Exchange Hybrid permissions
           Enter '5' - Set Exchange mail public folder permissions
           Enter '6' - Set MS-DS-Consistency-Guid permissions
           Enter '7' - Set password hash sync permissions
           Enter '8' - Set password writeback permissions
           Enter '9' - Set restricted permissions
           Enter '10' - Set unified group writeback permissions
           Enter '11' - Show AD object permissions
           Enter '12' - Set default AD Connector account permissions
           Enter '13' - Compare object read permissions when running in context of AD Connector account vs Admin account
           Enter 'B' - Go back to main troubleshooting menu
           Enter 'Q' - Quit

           Please make a selection: 4_
   ```
7. 在 `Account to Configure` 屏幕上，当收到消息提示“是否要配置现有连接器帐户或自定义帐户？” 时，输入 *E* 以选择现有连接器帐户（默认响应）：

   ```
   Account to Configure
   Would you like to configure an existing connector account or a custom account?
   [E] Existing Connector Account  [C] Custom Account  [?] Help (default is "E")  E_
   ```
8. 在 `Configured connectors and their related accounts` 屏幕上，当看到包含 `ADConnectorName`、`ADConnectorForest`、`ADConnectorAccountName` 和 `ADConnectorAccountDomain` 数据的行列表后，输入您想要配置的账户的连接器名称：

   ```
   Configured connectors and their related accounts:

   ADConnectorName  ADConnectorForest ADConnectorAccountName ADConnectorAccountDomain
   ---------------- ----------------- ---------------------- ------------------------
   corp.contoso.com corp.contoso.com  MSOL__<hex-digits>     domain.contoso.com
   test.local       test.local        MSOL__<hex-digits>     test.local

   Name of the connector who's account to configure: corp.contoso.com_
   ```

   **注意：** 在此屏幕中，“谁”一词显示为“谁”，尽管它应该是“谁”。
9. 选择 `Enter` 可对所有子对象的域根目录应用权限，或指定要为其设置权限的目标对象。 例如，可以指定用户所在的目标组织单位（OU）：

   ```
   To set permissions for a single target object, enter the DistinguishedName of the target AD
   object. Giving no input will set root permissions for all Domains in the Forest: _
   ```
10. 在`Update AdminSdHolders`屏幕中，当系统提示您是否“在更新这些权限时更新[AdminSDHolder](/zh-cn/windows-server/identity/ad-ds/plan/security-best-practices/appendix-c--protected-accounts-and-groups-in-active-directory#adminsdholder)容器？”时，仅当您在[Active Directory](/zh-cn/windows-server/identity/ad-ds/plan/security-best-practices/appendix-c--protected-accounts-and-groups-in-active-directory)中将受保护的帐户同步到Microsoft Entra ID时，才输入*Y*。 否则，输入 *N* 作为 `No` （默认响应）。

    ```
    Update AdminSdHolders
    Update AdminSDHolder container when updating with these permissions?
    [Y] Yes  [N] No  [?] Help (default is "N"): _
    ```

    备注

    不要将本地 AD 管理员帐户同步到 Microsoft Entra ID。 有关详细信息，请参阅[计划 Microsoft Entra 自助密码重置部署](/zh-cn/azure/active-directory/authentication/howto-sspr-deployment)[的](/zh-cn/azure/active-directory/authentication/howto-sspr-deployment#administrator-password-setting)“管理员密码设置”部分。
11. 在屏幕中 `Confirm` ，输入 *Y* 以确认 `Yes` 选择（默认响应）：

    ```
    Confirm
    Are you sure you want to perform this action?
    Performing the operation "Grant Exchange Hybrid permissions" on target "corp.contoso.com"
    [Y] Yes  [A] Yes to All  [N] No  [L] No to All  [S] Suspend  [?] Help (default is "Y"): y_
    ```

## 解决方案 2：在 PowerShell 中使用 ADSyncConfig 模块授予权限

备注

此解决方案也是建议的方法。

有关此解决方案的信息，请参阅[Microsoft Entra Connect：配置 AD DS 连接器帐户权限](/zh-cn/azure/active-directory/hybrid/connect/how-to-connect-configure-ad-ds-connector-account)[的](/zh-cn/azure/active-directory/hybrid/connect/how-to-connect-configure-ad-ds-connector-account#using-the-adsyncconfig-powershell-module)“使用 ADSyncConfig PowerShell 模块”部分。

## 解决方案 3：使用Active Directory 用户和计算机管理单元授予权限

警告

如果使用此方法在 Active Directory 中手动授予权限，可能会导致权限不足，从而导致意外结果。

1. 在具有相应域管理员权限的帐户上，选择**开始**，然后搜索并选择**Active Directory 用户和计算机**管理单元（*dsa.msc*）。
2. 在**“视图**”菜单中，如果高级功能**旁边**未显示复选标记，请选择该菜单项，以便可以查看高级功能。
3. 在控制台树中，找到表示域根的对象。 右键单击该对象，然后选择“ **属性**”。
4. 在 **“属性** ”对话框中，选择“ **安全** ”选项卡，然后选择“ **高级** ”按钮。
5. 在 **“高级安全设置”** 对话框中，选择“ **权限** ”选项卡，然后选择“ **添加** ”按钮。
6. **在“权限输入**”对话框中，输入下表中所述的设置。

   | 设置 | 动作 |
   | --- | --- |
   | **主体名称** | **选择“选择主体**”链接。 输入要向其应用权限的帐户的名称（Microsoft Entra Connect 使用的帐户），然后选择“ **确定**”。 |
   | **类型** 列表 | 选择**允许**。 |
   | **适用于** 列表 | 选择 **“后代用户”对象** 以显示所选主体允许的权限列表。 |
   | **属性** 选项 | 在您需要的每个权限属性选项上选中复选框。 滚动浏览属性列表以查找所需的属性。 属性选项名称可以包括**读取所有属性、**写入所有属性****、**读取 msDS-OperationsForAzTaskBL**、**读取 msDS-parentdistname** 等。 |

   [![Active Directory 用户和计算机管理单元中“权限条目”对话框的屏幕截图。](media/troubleshoot-permission-issue-sync-service-manager/permission-entry-dialog-box.png)](media/troubleshoot-permission-issue-sync-service-manager/permission-entry-dialog-box.png#lightbox)
7. 若要退出对话框并应用更改，请选择“ **确定** ”按钮三次。

## 解决方案 4：使用 dsacls 工具授予权限

警告

如果使用此方法在 Active Directory 中手动授予权限，可能会导致权限不足，从而导致意外结果。

若要授予域根目录下所有对象及其子对象读取和写入所有属性的权限，请运行以下 [dsacls](/zh-cn/previous-versions/windows/it-pro/windows-server-2012-R2-and-2012/cc771151(v=ws.11)) 命令：

```
dsacls.exe "DC=Contoso,DC=com" /G "CONTOSO\ADConnectAccount:RPWP;;" /I:S
```

在此命令中，`DC=Contoso,DC=com` 是您的域的可分辨名称，而 `CONTOSO\ADConnectAccount` 是 Microsoft Entra Connect 使用的域帐户。

## 已知问题

下表列出了导致 **权限问题** 错误的已知问题，但当前无法由列出的解决方案解决。

| 条件 | 效果 |
| --- | --- |
| **用户的 AdminCount** 属性大于零，即使用户不再是受保护组的成员。 | 由于未应用新权限，你会看到意外的同步结果或 **权限问题** 错误。 |
| Active Directory 中存在 [SDProp](/zh-cn/windows-server/identity/ad-ds/plan/security-best-practices/appendix-c--protected-accounts-and-groups-in-active-directory#sdprop) 问题。 | 应用 **解决方案后，权限问题** 错误仍然存在，因为 Active Directory 无法传播域中所有子对象的新权限。 |

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/troubleshoot-permission-issue-sync-service-manager)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
