# Microsoft Entra Connect 对象和属性的端到端故障排除

## 概要

本文旨在建立有关如何排查 Microsoft Entra ID 中的同步问题的常见做法。

当对象或属性无法与 Microsoft Entra ID 目录同步且同步引擎、应用程序事件查看器日志或Microsoft Entra 日志中未显示任何错误时，将使用此方法。 如果没有明显的错误，很容易在详细信息中丢失。 但是，通过使用最佳做法，可以隔离问题并为Microsoft 支持部门工程师提供见解。

将此故障排除方法应用于环境时，随着时间的推移，你将能够执行以下步骤：

- 从头到尾对同步引擎逻辑进行故障排除。
- 更有效地解决同步问题。
- 通过预测问题发生的步骤来更快地识别问题。
- 确定查看数据的起点。
- 确定最佳分辨率。

![Microsoft Entra Connect 流程图的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/aad-connect-flow-chart.png)

此处提供的步骤从本地 Active Directory 级别开始，并朝着 Microsoft Entra ID 前进。 这些步骤是同步的最常见方向。 但是，相同的原则适用于逆向方向（例如，对于属性写回）。

## 先决条件

若要更好地了解本文，请先阅读以下先决条件文章，以便更好地了解如何在不同源中搜索对象，以及如何检查对象的连接器和世系。

- [Microsoft Entra Connect：帐户和权限](/zh-cn/azure/active-directory/hybrid/reference-connect-accounts-permissions)
- [对未与 Microsoft Entra ID 同步的对象进行故障排除](/zh-cn/azure/active-directory/hybrid/tshoot-connect-object-not-syncing)
- [排查 Microsoft Entra Connect 同步的对象同步问题](/zh-cn/azure/active-directory/hybrid/tshoot-connect-objectsync)

## 无效的故障排除做法

`onPremisesSyncEnabled` Microsoft Entra ID 中的属性控制租户是否准备接受来自本地 AD DS 的对象同步。

排查对象或属性同步问题时，通常会在租户上禁用 DirSync。 可以使用 Graph 或 PowerShell 关闭目录同步。 但是，此过程可能会导致中断。

在租户级别禁用 DirSync 会触发复杂而漫长的后端作，以便将颁发机构源（SoA）从本地 Active Directory 传输到Microsoft Entra ID，并为租户上的所有同步对象交换 Online。 此作需要将每个对象从 `onPremisesSyncEnabled=True` 仅限云的对象（`onPremisesSyncEnabled=<null>`）转换为仅限云的对象，并清理从本地 AD DS 同步的所有阴影属性（例如， `ShadowUserPrincipalName` 和 `ShadowProxyAddresses`）。 根据租户的大小，此作可能需要 72 小时以上，并且无法预测其完成时间。

请勿使用此方法来排查同步问题，因为此类作可能会导致更多的伤害，并且无法修复根本问题。 在完成此禁用作之前，无法再次启用 DirSync。 重新启用 DirSync 后，Entra Connect 服务器必须与现有的 Microsoft Entra ID 对象匹配所有本地对象。

仅在以下方案中支持禁用 DirSync：

- 你正在解除本地同步服务器的授权，并且想要从云而不是混合标识中继续完全管理标识。
- 租户中有一些要保留为仅限云的Microsoft Entra ID 中的同步对象，并永久从本地 AD 中删除。
- 当前使用自定义属性作为 Entra Connect 中的 SourceAnchor（例如 employeeId），并且正在重新安装 AADC 以开始使用 **ms-Ds-Consistency-Guid/ObjectGuid** 作为新的 SourceAnchor 属性（反之亦然）。
- 邮箱迁移策略中的某些方案可能会导致潜在问题。

在某些情况下，可能需要暂时停止同步或手动控制 Entra Connect 同步周期。 例如，可能需要暂停同步才能一次运行一个同步步骤。 可以通过运行以下 cmdlet 来停止同步计划程序，而不是禁用 DirSync：

```
Set-ADSyncScheduler -SyncCycleEnabled $false
```

准备就绪后，通过运行以下 cmdlet 来还原正常的同步计划程序：

```
Start-ADSyncSyncCycle
```

## 术语表

| Acronym/abbr acronym | 名称/说明 |
| --- | --- |
| AADC | Microsoft Entra Connect |
| AADCA | Microsoft Entra 连接器帐户 |
| AADCS | Microsoft Entra 连接器空间 |
| AADCS:AttributeA | Microsoft Entra 连接器空间中的属性“A” |
| ACL | 访问控制列表（也称为 ADDS 权限） |
| ADCA | AD 连接器帐户 |
| ADCS | Active Directory 连接器空间 |
| ADCS:AttributeA | Active Directory 连接器空间中的属性“A” |
| ADDS 或 AD | Active Directory 域服务 |
| CS | 连接器空间 |
| MV | Metaverse |
| MSOL 帐户 | 自动生成的 AD 连接器帐户 (MSOL\_########) |
| MV:AttributeA | Metaverse 对象中的属性“A” |
| SoA | 颁发机构来源 |

## 步骤 1：ADDS 与 ADCS 之间的同步

### 步骤 1 的目标

确定对象或属性是否存在并在 ADCS 中保持一致。 如果可以在 ADCS 中找到对象，并且所有属性都具有预期值，请转到 [步骤 2](#step-2-synchronization-between-adcs-and-mv)。

![A D 连接器空间 A D 复制的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/adcs-ad-replication.png)

### 步骤 1 的说明

ADDS 和 ADCS 之间的同步发生在导入步骤中，这是 AADC 从源目录读取数据并将数据存储在数据库中的那一刻。 也就是说，在连接器空间中暂存数据时。 在从 AD 导入增量期间，AADC 请求给定目录水印之后发生的所有新更改。 此调用由 AADC 通过对 Active Directory 复制服务使用目录服务 DirSync 控件启动。 此步骤提供最后一个水印作为最后一个成功的 AD 导入，并提供 AD 从何时检索所有 （delta） 更改的时间点引用。 完全导入是不同的，因为 AADC 从 ADCS 导入同步范围中的所有数据，然后标记为已过时（并删除）仍在 ADCS 中的所有对象，但不是从 AD 导入的。 AD 和 AADC 之间的所有数据都通过 LDAP 传输，默认加密。

![A D C 连接选项对话框的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/aadc-connection-options.png)

如果与 AD 的连接成功，但 ADCS 中不存在对象或属性（假设域或对象处于同步范围内），则问题最有可能涉及 ADDS 权限。 ADCA 需要对 AD 中的对象具有最少的读取权限才能将数据导入 ADCS。 默认情况下，MSOL 帐户具有所有用户、组和计算机属性的显式读/写权限。 但是，如果满足以下条件，这种情况可能仍然存在问题：

- AADC 使用自定义 ADCA，但它在 AD 中未提供足够的权限。
- 父 OU 已阻止继承，这会阻止从域的根目录传播权限。
- 对象或属性本身已阻止继承，这会阻止权限传播。
- 对象或属性具有显式的拒绝权限，该权限阻止 ADCA 读取它。

### Active Directory 故障排除

#### 与 AD 的连接

在 Synchronization Service Manager 中，“从 AD 导入”步骤显示连接状态**下**与哪个域控制器联系。 当存在影响 AD 的连接问题时，你很可能会看到一个错误。

![屏幕截图显示了“从 A D 步骤导入”中的“连接状态”区域。](media/troubleshoot-aad-connect-objects-attributes/import-from-ad-connection-status.png)

如果必须进一步排查 AD 的连接问题，尤其是在Microsoft Entra Connect 服务器中未显示错误，或者仍在安装产品的过程中，请先使用 [ADConnectivityTool](/zh-cn/azure/active-directory/hybrid/how-to-connect-adconnectivitytools#adconnectivitytool-during-installation)。

ADDS 的连接问题具有以下原因：

- AD 凭据无效。 例如，ADCA 已过期或密码已更改。
- “失败搜索”错误，当 DirSync 控件不与 AD 复制服务通信时发生，通常是由于高网络数据包碎片。
- AD 中存在名称解析问题（DNS）时出现的“no-start-马”错误。
- 其他问题可能是由名称解析问题、网络路由问题、阻止的网络端口、高网络数据包碎片、没有可用的可写 DC 等引起的。 在这种情况下，可能需要让目录服务或网络支持团队参与帮助进行故障排除。

**故障排除摘要：**

- 确定使用哪个域控制器。
- 使用首选域控制器以相同的域控制器为目标。
- 正确标识 ADCA。
- 使用 ADConnectivityTool 确定问题。
- 使用 LDP 工具尝试使用 ADCA 绑定到域控制器。
- 请联系目录服务或网络支持团队，帮助你进行故障排除。

#### 运行同步疑难解答

对 AD 连接进行故障排除后，请运行 [“对象同步](/zh-cn/azure/active-directory/hybrid/tshoot-connect-objectsync) 故障排除”工具，因为这可以检测对象或属性不同步的最明显原因。

![Microsoft Entra Connect 故障排除屏幕的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/aadconnect-troubleshooting.png)

### AD 权限

缺少 AD 权限可能会影响同步的两个方向：

- 从 ADDS 导入 ADCS 时，缺少权限可能会导致 AADC 跳过对象或属性，以便 AADC 无法在导入流中获取 ADDS 更新。 发生此错误的原因是 ADCA 没有足够的权限读取对象。
- 从 ADCS 导出到 ADDS 时，缺少权限将生成“权限问题”导出错误。

若要检查权限，请打开 **AD 对象的“属性**”窗口，选择“安全>）来检查对象的允许/拒绝 ACL。 可以按 **类型** 对列内容进行排序，以查找所有“拒绝”权限。 AD 权限可能会有所不同。 但是，默认情况下，对于“Exchange 受信任的子系统”，可能只看到一个“拒绝 ACL”。大多数权限将标记为 **“允许**”。

以下默认权限最相关：

- 经过身份验证的用户

  ![屏幕截图显示了经过身份验证的用户。](media/troubleshoot-aad-connect-objects-attributes/authenticated-users.png)
- 所有人

  ![屏幕截图显示“允许”选项设置为“每个人”。](media/troubleshoot-aad-connect-objects-attributes/allow-everyone.png)
- 自定义 ADCA 或 MSOL 帐户

  ![屏幕截图显示了自定义 ADCA 或 MSOL 帐户。](media/troubleshoot-aad-connect-objects-attributes/custom-adca-msol-account.png)
- Windows 2000 以前版本兼容的访问

  ![屏幕截图显示了预 Windows 2000 兼容访问。](media/troubleshoot-aad-connect-objects-attributes/pre-windows-2000-comp-access.png)
- SELF

  ![屏幕截图显示允许的 SELF 权限。](media/troubleshoot-aad-connect-objects-attributes/allow-self.png)

排查权限问题的最佳方式是在 AD 用户和计算机**控制台中使用“有效访问”功能**。 此功能检查要排除的目标对象或属性上给定帐户（ADCA）的有效权限。

![屏幕截图显示“高级安全设置”窗口中“有效访问”选项卡下的信息。](media/troubleshoot-aad-connect-objects-attributes/advanced-security-settings.png)

重要

对 AD 权限进行故障排除可能很困难，因为 ACL 中的更改不会立即生效。 始终认为此类更改受 AD 复制的约束。

**故障排除摘要：**

- 确定使用哪个域控制器。
- 使用首选域控制器以相同的域控制器为目标。
- 正确标识 ADCA。
- [使用“配置 AD DS 连接器帐户权限](/zh-cn/azure/active-directory/hybrid/how-to-connect-configure-ad-ds-connector-account)”工具。
- 在 AD 用户和计算机中使用“有效访问”功能。
- 使用 LDP 工具绑定到具有 ADCA 的域控制器，并尝试读取失败的对象或属性。
- 暂时将 ADCA 添加到企业管理员或域管理员，然后重启 ADSync 服务。

警告

请勿将此用作权限问题的永久解决方案。 确定权限问题后，从任何高特权组中删除 ADCA，并将所需的 AD 权限直接授予 ADCA。

备注

参与目录服务或网络支持团队，帮助你排查这种情况。

#### AD 复制

此问题不太可能影响 Microsoft Entra Connect，因为它会导致更大的问题。 但是，当Microsoft Entra Connect 使用延迟复制从域控制器导入数据时，它不会从 AD 导入最新信息，这会导致 AD 中最近创建或更改的对象或属性不会同步到 Microsoft Entra ID，因为它未复制到Microsoft Entra Connect 的域控制器。 若要验证此问题，请检查 AADC 用于导入的域控制器（请参阅“连接到 AD”），并使用 **AD 用户和计算机** 控制台直接连接到此服务器（请参阅 **下一映像中的更改域控制器** ）。 然后，验证此服务器上的数据是否对应于最新数据，以及它是否与相应的 ADCS 数据保持一致。 在此阶段，AADC 将在域控制器和网络层上生成更大的负载。

![Active Directory 的“更改域控制器”选项的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/change-domain-controller.png)

另一种方法是使用 RepAdmin 工具检查所有域控制器上的对象的复制元数据，从所有域控制器获取值，以及检查域控制器之间的复制状态：

- 来自所有域控制器的属性值：

  `RepAdmin /showattr * "DC=contoso,DC=com" /subtree /filter:"sAMAccountName=User01" /attrs:pwdLastSet,UserPrincipalName`

  ![使用 showattr 的 RepAdmin 工具的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/repadmin-showattr.png)
- 来自所有 DC 的对象元数据：

  `RepAdmin /showobjmeta * "CN=username,DC=contoso,DC=com" > username-ObjMeta.txt`

  ![RepAdmin 工具的屏幕截图，其中显示了 showobjmeta 命令。](media/troubleshoot-aad-connect-objects-attributes/repadmin-showobjmeta.png)
- AD 复制摘要

  `RepAdmin /replsummary`

  ![使用 replsummary 命令的 RepAdmin 工具的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/repadmin-replsummary.png)

**故障排除摘要：**

- 确定使用哪个域控制器。
- 比较域控制器之间的数据。
- 分析 RepAdmin 结果。
- 请联系目录服务或网络支持团队，帮助解决问题。

#### 域和 OU 更改，以及在 ADDS 连接器中筛选或排除的对象类型或属性

- **更改域或 OU 筛选需要完全导入**

  请记住，即使已确认域或 OU 筛选，对域或 OU 筛选所做的任何更改只有在运行完整导入步骤后才会生效。
- **Microsoft Entra 应用和属性筛选的属性筛选**

  未同步的属性的易失方案是，Microsoft Entra Connect 配置了 [Microsoft Entra 应用和属性筛选](/zh-cn/azure/active-directory/hybrid/how-to-connect-install-custom#azure-ad-app-and-attribute-filtering) 功能。 若要检查该功能是否已启用，以及针对哪些属性，请从**故障排除任务**获取[常规诊断报告](/zh-cn/entra/identity/hybrid/connect/tshoot-connect-objectsync#troubleshooting-task)，或从 PowerShell 运行`(Get-ADSyncGlobalSettings).Parameters | where Name -eq 'Microsoft.OptionalFeature.FilterAAD' | select Name, Value`。
- **ADDS 连接器配置中排除的对象类型**

  这种情况不会像用户和组一样常见。 但是，如果 ADCS 中缺少特定对象类型的所有对象，则检查 ADDS 连接器配置中启用的对象类型可能很有用。

`Get-ADSyncConnector`使用 cmdlet 检索连接器上启用的对象类型，如下图所示。

```
$connectorName = "Contoso.com"
(Get-ADSyncConnector | where Name -eq $connectorName).ObjectInclusionList`
```

以下列表显示应默认启用的对象类型（仅 `publicFolder` 当启用邮件的公用文件夹功能时才存在该对象类型）。

![显示 Get-ADSyncConnector 对象类型的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/get-adsyncconnector-objects.png)

- **ADCS 中排除的属性**

  同样，如果所有对象缺少该属性，请检查是否在 AD 连接器上选择了该属性。

  若要在 ADDS 连接器中检查已启用的属性，请使用同步管理器，如下图所示，或运行以下 PowerShell cmdlet：

  ```
  $connectorName = "Contoso.com"
  (Get-ADSyncConnector | where Name -eq $connectorName).AttributeInclusionList
  ```

  ![AD 连接器同步管理器的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/ad-connector-sync-manager.png)

  重要

  不支持在 Synchronization Service Manager 中包含或排除对象类型或属性。

**故障排除摘要：**

- 检查 [Microsoft Entra 应用和属性筛选](/zh-cn/azure/active-directory/hybrid/how-to-connect-install-custom#azure-ad-app-and-attribute-filtering) 功能
- 验证对象类型是否包含在 ADCS 中。
- 验证该属性是否包含在 ADCS 中。
- 运行完整导入。

#### 步骤 1 的资源

主要资源：

- Get-ADSyncConnectorAccount - 标识 AADC 使用的正确连接器帐户
- [ADConnectivityTool](/zh-cn/azure/active-directory/hybrid/how-to-connect-adconnectivitytools#adconnectivitytool-during-installation)
- 识别 ADDS 的连接问题
- Trace-ADSyncToolsADImport （ADSyncTools） - 从 ADDS 导入的跟踪数据
- LDIFDE - 从 ADDS 转储对象以比较 ADDS 和 ADCS 之间的数据
- LDP - 在 ADCA 的安全上下文中测试 AD 绑定连接和读取对象的权限
- DSACLS - 比较和评估 ADDS 权限
- Set-ADSync< 功能 >权限 - 在 ADDS 中应用默认 AADC 权限
- RepAdmin - 检查 AD 对象元数据和 AD 复制状态

## 步骤 2：ADCS 与 MV 之间的同步

![屏幕截图显示了 A D C S 到 MetaVerse 流程图。](media/troubleshoot-aad-connect-objects-attributes/adcs-metaverse-flow-chart.png)

### 步骤 2 的目标

此步骤检查对象或属性是否从 CS 流向 MV（换句话说，对象或属性是否投影到 MV）。 在此阶段，请确保对象存在，或者属性在 ADCS 中正确（步骤 1 [中](#step-1-synchronization-between-adds-and-adcs)介绍），然后开始查看对象的同步规则和世系。

### 步骤 2 的说明

ADCS 和 MV 之间的同步发生在增量/完全同步步骤中。 此时，AADC 读取 ADCS 中的暂存数据，处理所有同步规则，并更新相应的 MV 对象。 此 MV 对象将包含指向 CS 对象（或连接器）的链接，这些链接指向其属性和同步步骤中应用的同步规则的世系。 在此阶段，AADC 在 SQL Server（或 LocalDB）和网络层上生成更多负载。

### 对对象的 ADCS > MV 进行故障排除

- **检查入站同步规则以预配**

  在 ADCS 中存在但 MV 中缺少的对象表示，任何应用于该对象的预配同步规则都没有范围筛选器。 因此，对象未投影到 MV。 如果禁用或自定义同步规则，则可能会出现此问题。

  若要获取入站预配同步规则的列表，请运行以下命令：

  `Get-ADSyncRule | where {$_.Name -like "In From AD*" -and $_.LinkType -eq "Provision"} | select Name,Direction,LinkType,Precedence,Disabled | ft`

  ![屏幕截图显示 Get-ADSyncRule 命令用于检查入站预配规则。](media/troubleshoot-aad-connect-objects-attributes/get-adsyncrule.png)
- **检查 ADCS 对象的世系**

  可以通过在“搜索连接器空间”中搜索“DN 或定位点”，从 ADCS 中检索失败的对象。在“ **世系** ”选项卡上，你可能会看到对象是 **断开连接器** （没有指向 MV 的链接），世系为空。 此外，检查对象是否有任何错误，以防出现同步错误选项卡。

  ![A D C S 中的连接器空间对象属性的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/connector-space-object-properties.png)
- **在 ADCS 对象上运行预览**

  选择**“预览****>生成预览提交预览**>”以查看对象是否投影到 MV。 如果是这种情况，则完全同步周期应针对同一情况下的其他对象解决问题。

  ![A D C 对象预览屏幕的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/adcs-object-preview.png)

  ![A D C S 中“源对象详细信息”屏幕的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/adcs-source-object-details.png)
- **将对象导出到 XML**

  有关更详细的分析（或脱机分析），可以使用 cmdlet 收集与对象 `Export-ADSyncToolsObjects` 相关的所有数据库数据。 此导出的信息将有助于确定筛选出对象的规则。 换句话说，预配同步规则中的入站范围筛选器阻止将对象投影到 MV。

  下面是语法的 `Export-ADSyncToolsObjects` 一些示例：

  ```
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  Install-Module ADSyncTools

  Import-Module ADSyncTools
  Export-ADSyncToolsObjects -DistinguishedName 'CN=TestUser,OU=Sync,DC=Contoso,DC=com' -ConnectorName 'Contoso.com' -ExportSerialized
  Export-ADSyncToolsObjects -ObjectId '{aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb}' -Source Metaverse -ExportSerialized
  ```

  提示

  若要读取导出的数据，请使用 `Import-Clixml <filename>.xml` cmdlet。

#### 故障排除摘要 （对象）

- 检查“来自 AD”入站预配规则的范围筛选器。
- 创建对象的预览。
- 运行完全同步周期。
- 使用 `Export-ADSyncToolsObjects` cmdlet 导出对象数据。

#### 对属性的 ADCS > MV 进行故障排除

1. **标识属性的入站同步规则和转换规则**

   每个属性都有自己的转换规则集，这些规则负责将值从 ADCS 定向到 MV。 第一步是确定哪些同步规则包含要进行故障排除的属性的转换规则。

   确定哪些同步规则具有给定属性的转换规则的最佳方式是使用同步规则编辑器**的**内置筛选功能。

   ![A D C S 中的同步规则编辑器的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/sync-rules-editor.png)
2. **检查 ADCS 对象的世系**

   CS 和 MV 之间的每个连接器（或链接）都有一个世系，其中包含有关应用于该 CS 对象的同步规则的信息。 上一步将告诉你哪些入站同步规则（无论是预配还是联接同步规则）必须存在于对象的世系中，才能将正确的值从 ADCS 流向 MV。 通过检查 ADCS 对象的世系，可以确定该同步规则是否应用于该对象。

   ![连接器空间对象属性世系屏幕的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/connector-space-object-properties-lineage.png)

   如果有多个连接器（多个 AD 林）链接到 MV 对象，则可能需要检查 **Metaverse 对象属性** ，以确定哪个连接器将属性值贡献给要进行故障排除的属性。 标识连接器后，检查该 ADCS 对象的世系。

   ![Metaverse 对象属性屏幕的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/metaverse-object-properties.png)
3. **检查入站同步规则上的范围筛选器**

   如果启用了同步规则，但对象世系中不存在，则应通过同步规则的范围筛选器筛选掉该对象。 通过检查同步规则的范围筛选器、ADCS 对象上的数据以及同步规则是启用或禁用的，应该能够确定同步规则未应用于 ADCS 对象的原因。

   下面是负责同步 Exchange 属性的同步规则中常见麻烦的范围筛选器的示例。 如果对象具有 **mailNickName** 的 null 值，则转换规则中的 Exchange 属性都不会流向Microsoft Entra ID。

   ![“查看入站同步规则”屏幕的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/inbound-sync-rules.png)
4. **在 ADCS 对象上运行预览版**

   如果无法确定 ADCS 对象的世系中缺少同步规则的原因，请使用 **“生成预览** ”和 **“提交预览** ”来运行预览，以便完全同步该对象。 如果属性在 MV 中更新并具有预览，则完全同步周期应针对同一情况下的其他对象解决问题。
5. **将对象导出到 XML**

   有关更详细的分析或脱机分析，可以使用 cmdlet 收集与对象 `Export-ADSyncToolsObjects` 相关的所有数据库数据。 此导出的信息可以帮助你确定对象上缺少哪些同步规则或转换规则，从而阻止将属性投影到 MV（请参阅 `Export-ADSyncToolsObjects` 本文前面的示例）。

#### 故障排除摘要 （对于属性）

- 确定负责将属性流向 MV 的正确同步规则和转换规则。
- 检查对象的世系。
- 检查是否已启用同步规则。
- 检查对象世系中缺少的同步规则的范围筛选器。

#### 同步规则管道的高级故障排除

如果在同步规则处理方面必须进一步调试 ADSync 引擎（也称为 MiiServer），可以在 .config 文件（C：\Program Files\Microsoft Azure AD Sync\Bin\miiserver.exe.config）上启用 ETW 跟踪。 此方法生成一个广泛的详细文本文件，用于显示同步规则的所有处理。 但是，可能很难解释所有信息。 使用此方法作为最后手段，或者如果此方法由Microsoft 支持部门指示。

#### 步骤 2 的资源

- 同步服务管理器用户界面
- 同步规则编辑器
- Export-ADSyncToolsObjects cmdlet（用于导出AD同步工具对象的命令）
- Start-ADSyncSyncCycle -PolicyType 初始
- ETW 跟踪 SyncRulesPipeline （miiserver.exe.config）

## 步骤 3：MV 与 AADCS 之间的同步

![M V 和 A D C S 流程图的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/mv-aadcs-flow-chart.png)

### 步骤 3 的目标

此步骤检查对象或属性是否从 MV 流向 AADCS。 此时，请确保对象存在，或者属性在 ADCS 和 MV 中正确（步骤 1 和步骤 2 中介绍）。 然后，检查对象的同步规则和世系。 此步骤类似于 [步骤 2](#step-2-synchronization-between-adcs-and-mv)，其中检查了从 ADCS 到 MV 的入站方向，但是，在此阶段，我们将专注于从 MV 流向 AADCS 的出站同步规则和属性。

### 步骤 3 的说明

当 AADC 读取 MV 中的数据、处理所有同步规则并更新相应的 AADCS 对象时，MV 与 AADCS 之间的同步发生在增量/完全同步步骤中。 此 MV 对象将包含 CS 链接（也称为连接器），这些链接指向导致其属性的 CS 对象以及同步步骤中应用的同步规则的世系。 此时，AADC 在 SQL Server（或 localDB）和网络层上生成更多负载。

#### 对对象的 MV 到 AADCS 进行故障排除

1. **检查出站同步规则进行预配**

   MV 中存在但 AADCS 中缺少的对象表示，对应用于该对象的任何预配同步规则没有范围筛选器。 例如，请参阅下图中显示的“Out to Microsoft Entra ID”同步规则。 因此，未在 AADCS 中预配对象。 如果禁用或自定义同步规则，则可能会出现此错误。

   若要获取入站预配同步规则的列表，请运行以下命令：

   `Get-ADSyncRule | where {$_.Name -like "Out to AAD*" -and $_.LinkType -eq "Provision"} | select Name,Direction,LinkType,Precedence,Disabled | ft`

   ![用于检查出站同步规则的 Get-ADSyncRule 的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/outbound-sync-rules.png)
2. **检查 ADCS 对象的世系**

   若要从 MV 检索失败的对象，请使用 **Metaverse 搜索**，然后检查连接器选项卡。在此选项卡上，可以确定 MV 对象是否链接到 AADCS 对象。 此外，检查对象是否有任何错误，以防存在同步错误选项卡。

   ![Metaverse 搜索屏幕的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/metaverse-search.png)

   如果没有 AADCS 连接器，则对象很可能设置为 **cloudFiltered=True**。 可以通过检查与 cloudFiltered **值一起参与**的同步规则的 MV 属性来验证对象是否经过云筛选。
3. **在 AADCS 对象上运行预览版**

   选择>，以确定对象是否连接到 AADCS。 如果是这样，则完全同步周期应解决同一情况下其他对象的问题。
4. **将对象导出到 XML**

   有关更详细的分析或脱机分析，可以使用 cmdlet 收集与对象 `Export-ADSyncToolsObjects` 相关的所有数据库数据。 此导出的信息以及（出站）同步规则配置可以帮助确定哪个规则正在筛选出对象，并且可以确定预配同步规则中的哪些出站范围筛选器阻止对象与 AADCS 连接。

   下面是语法的 `Export-ADSyncToolsObjects` 一些示例：

```
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Install-Module ADSyncTools

Import-Module ADSyncTools
Export-ADSyncToolsObjects -DistinguishedName 'CN=TestUser,OU=Sync,DC=Contoso,DC=com' -ConnectorName 'Contoso.com' -ExportSerialized
Export-ADSyncToolsObjects -ObjectId '{aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb}' -Source Metaverse -ExportSerialized
```

提示

若要读取导出的数据，请使用 `Import-Clixml <filename>.xml`

#### 对象的故障排除摘要

- 检查“Out to Microsoft Entra ID”出站预配规则上的范围筛选器。
- 创建对象的预览。
- 运行完全同步周期。
- 使用 `Export-ADSyncToolsObjects` cmdlet 导出对象数据。

#### 排查 MV 到 AADCS 的属性问题

1. **标识属性的出站同步规则和转换规则**

   每个属性都有自己的转换规则集，这些规则负责将值从 MV 流向 AADCS。 首先确定哪些同步规则包含要进行故障排除的属性的转换规则。

   确定哪些同步规则具有给定属性的转换规则的最佳方式是使用同步规则编辑器的内置筛选功能。

   ![同步规则编辑器的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/view-manage-sync-rules.png)
2. **检查 ADCS 对象的世系**

   CS 和 MV 之间的每个连接器（或链接）都有一个世系，其中包含有关应用于该 CS 对象的同步规则的信息。 上一步将告诉你哪些出站同步规则（无论是预配还是联接同步规则）必须存在于对象的世系中，才能将正确的值从 MV 流向 AADCS。 通过检查 AADCS 对象的世系，可以确定该同步规则是否已应用于该对象。

   ![屏幕截图显示了 A D C S 对象上的“世系”选项卡详细信息。](media/troubleshoot-aad-connect-objects-attributes/connector-space-object-properties-run.png)
3. **检查出站同步规则上的范围筛选器**

   如果启用了同步规则，但对象世系中不存在同步规则，则应通过同步规则的范围筛选器将其筛选掉。 通过检查同步规则的范围筛选器的存在以及 MV 对象上的数据以及同步规则是启用或禁用的，你应该能够确定同步规则为何未应用于 AADCS 对象。
4. **在 AADCS 对象上运行预览**

   如果确定 ADCS 对象的世系中缺少同步规则的原因，请运行使用 **生成预览** 和 **提交预览的预览** 来完全同步该对象。 如果具有预览功能在 MV 中更新了该属性，则完全同步周期应修复同一情况下其他对象的问题。
5. **将对象导出到 XML**

   有关更详细的分析或脱机分析，可以使用 cmdlet 收集与对象 `Export-ADSyncToolsObjects` 相关的所有数据库数据。 此导出的信息以及（出站）同步规则配置可帮助确定该属性无法流向 AADCS 的对象中缺少哪些同步规则或转换规则（请参阅 `Export-ADSyncToolsObjects` 前面的示例）。

#### 属性的故障排除摘要

- 确定负责将属性流向 AADCS 的正确同步规则和转换规则。
- 检查对象的世系。
- 检查同步规则是否已启用。
- 检查对象世系中缺少的同步规则的范围筛选器。

### 排查同步规则管道问题

如果在同步规则处理方面必须进一步调试 ADSync 引擎（也称为 MiiServer），可以在 .config 文件（C：\Program Files\Microsoft Azure AD Sync\Bin\miiserver.exe.config）上启用 ETW 跟踪。 此方法生成一个广泛的详细文本文件，用于显示同步规则的所有处理。 但是，可能很难解释所有信息。 仅将此方法用作最后手段，或者如果此方法由Microsoft 支持部门指示。

### 资源

- Synchronization Service Manager
- 同步规则编辑器
- Export-ADSyncObjects cmdlet（导出AD同步对象命令）
- Start-ADSyncSyncCycle -PolicyType 初始
- ETW 跟踪 SyncRulesPipeline （miiserver.exe.config）

## 步骤 4：AADCS 与 Entra ID 之间的同步

![A D C S 与 Microsoft Entra ID 之间的同步流程图的屏幕截图。](media/troubleshoot-aad-connect-objects-attributes/sync-aadcs-azuread.png)

### 步骤 4 的目标

此阶段将 AADCS 对象与Microsoft Entra ID 中预配的相应对象进行比较。

### 步骤 4 的说明

导入和导出数据到 Microsoft Entra ID 所涉及的多个组件和进程可能会导致以下问题：

- 连接到 Internet
- 内部防火墙和 ISP 连接（例如阻止的网络流量）
- DirSync Webservice 前面Microsoft Entra 网关（也称为 AdminWebService）
- The DirSync Webservice API
- Microsoft Entra Core 目录服务

幸运的是，影响这些组件的问题通常会在可以通过Microsoft 支持部门跟踪的事件日志中生成错误。 因此，这些问题不适用于本文。 然而，仍有一些可以检查的“沉默”问题。

### AADCS 故障排除

- **导出到 Microsoft Entra ID 的多个活动 AADC 服务器**

  在Microsoft Entra ID 中的对象来回翻转属性值的常见方案中，有多个活动Microsoft Entra Connect 服务器，其中一台服务器与本地 AD 失去联系，但仍连接到 Internet，并且能够将数据导出到 Microsoft Entra ID。 因此，每当此“过时”服务器从 Microsoft Entra ID 导入由其他活动服务器创建的同步对象上的更改时，同步引擎都会根据 ADCS 中的过时 AD 数据还原该更改。 此方案中的典型症状是，在 AD 中进行更改，该更改已同步到 Microsoft Entra ID，但更改将在几分钟后还原为原始值（最多 30 分钟）。 若要快速缓解此问题，请返回到已解除授权的任何旧服务器或虚拟机，并检查 ADSync 服务是否仍在运行。
- **使用 DirSyncOverrides 的移动属性**

  当管理员使用旧版 MSOnline 或 AzureAD PowerShell 模块时，或者如果用户转到 Office 门户并更新 `Mobile` 属性，更新后的电话号码将在Microsoft Entra ID 中覆盖，尽管对象已从本地 AD （`onPremisesSyncEnabled=true`） 同步。

  与此更新一起，Microsoft Entra ID 还会设置一个 `DirSyncOverrides` 对象，以标记此用户在 Microsoft Entra ID 中包含移动电话号码“覆盖”。 从此开始，将忽略源自本地的移动属性的任何更新，因为此属性将不再由本地 AD 管理。

  有关 *BypassDirSyncOverrides* 功能以及如何将Microsoft Entra ID 中的`Mobile`同步和`otherMobile`属性还原到本地 Active Directory的详细信息，请参阅[如何使用 Microsoft Entra 租户](/zh-cn/azure/active-directory/hybrid/how-to-bypassdirsyncoverrides)的 BypassDirSyncOverrides 功能。
- **UserPrincipalName 更改不会在 Microsoft Entra ID 中更新**

  如果在 Microsoft Entra ID 中未更新该 `UserPrincipalName` 属性，而其他属性则可能会按预期同步，但租户上可能未启用名为 [SynchronizeUpnForManagedUsers](/zh-cn/azure/active-directory/hybrid/how-to-connect-syncservice-features#synchronize-userprincipalname-updates) 的功能。

  在添加此功能之前，在Microsoft Entra ID 中预配用户并分配许可证后，本地对 UPN 的任何更新将 *静默* 忽略。 管理员必须使用旧版 MSOnline 或 AzureAD PowerShell 直接在 Microsoft Entra ID 中更新 UPN。 添加此功能后，UPN 的任何更新都将流向Microsoft Entra，而不考虑用户是否获得许可（托管）。

  备注

  启用此功能后，无法禁用此功能。

  **如果用户未获得许可，UserPrincipalName** 更新将起作用。 但是，如果没有 [SynchronizeUpnForManagedUsers](/zh-cn/azure/active-directory/hybrid/how-to-connect-syncservice-features#synchronize-userprincipalname-updates) 功能，则用户预配后 UserPrincipalName 会更改，并分配有许可证，该许可证不会在 Microsoft Entra ID 中更新。 请注意，Microsoft不会代表客户禁用此功能。
- **无效字符和 ProxyCalc 内部**

  涉及不产生任何同步错误的无效字符的问题在 UserPrincipalName **和 ProxyAddresses **属性中比较麻烦，因为 ProxyCalc 处理中的**级联效果会**以无提示方式**放弃从本地 AD 同步**的值。 出现这种情况，如下所示：

  1. Microsoft Entra ID 中生成的 **UserPrincipalName 将是 **MailNickName**** 或 **CommonName** @ （at） 初始域。 例如，John.Smith@Contoso.com**Microsoft Entra ID 中的 UserPrincipalName** 可能会变为smithj@Contoso.onmicrosoft.com因为本地 AD 中的 UPN 值中有一个不可见字符。
  2. 如果 ProxyAddress **包含空格字符，**ProxyCalc** 将放弃该字符，并根据初始域上的 MailNickName **自动生成电子邮件地址**。** 例如，“SMTP： John.Smith@Contoso.com”不会出现在Microsoft Entra ID 中，因为它在冒号后包含空格字符。
  3. **包含空格字符的 UserPrincipalName** 或**包含不可见字符的 ProxyAddress** 将导致相同的问题。

     若要排查 UserPrincipalName **或 **ProxyAddress** 中**无效字符的问题，请检查从 LDIFDE 或 PowerShell 导出到文件的本地 AD 中存储的值。 检测不可见字符的一个简单技巧是复制导出文件的内容，然后将其粘贴到 PowerShell 窗口中。 不可见字符将替换为问号（？），如以下示例所示。

     ![屏幕截图显示了对 UserPrincipalName 或 ProxyAddress 进行故障排除的示例。](media/troubleshoot-aad-connect-objects-attributes/userprinciplename.png)
- **ThumbnailPhoto 属性 （KB4518417）**

  有一个一般误解，即首次从 AD 同步 ThumbnailPhoto 后，无法再更新它，这只是部分事实。

  通常，Microsoft Entra ID 中的 ThumbnailPhoto 会不断更新。 但是，如果更新后的图片不再由相应的工作负荷或合作伙伴（例如 EXO 或 SfBO）从 Microsoft Entra ID 检索，则会出现问题。 此问题会导致图片未从本地 AD 同步到 Microsoft Entra ID 的误报。

  排查 ThumbnailPhoto 问题的基本步骤：

  1. 请确保映像正确存储在 AD 中，且不超过大小限制 100 KB。
  2. 在帐户门户中检查图像，或通过 Graph 调用 [Get profilePhoto](/zh-cn/graph/api/profilephoto-get) 。
  3. 如果 ADDS （或 Entra ID） thumbnailPhoto 具有正确的图像，但它在其他联机服务上不是正确的图像，则以下条件可能适用：
  - 用户的邮箱包含 HD 图像，不接受来自 Microsoft Entra thumbnailPhoto 的低分辨率图像。 解决方案是直接更新用户的邮箱映像。
  - 用户的邮箱映像已正确更新，但仍会看到原始图像。 解决方案是等待至少六个小时才能在 Office 365 用户门户中或Azure 门户中查看更新后的映像。

## 其他资源

- [排查同步过程中发生的错误](/zh-cn/azure/active-directory/hybrid/tshoot-connect-sync-errors)
- [排查 Microsoft Entra Connect 同步的对象同步问题](/zh-cn/azure/active-directory/hybrid/tshoot-connect-objectsync)
- [对未与 Microsoft Entra ID 同步的对象进行故障排除](/zh-cn/azure/active-directory/hybrid/tshoot-connect-object-not-syncing)
- [Microsoft Entra Connect 单对象同步](/zh-cn/azure/active-directory/hybrid/how-to-connect-single-object-sync)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/troubleshoot-aad-connect-objects-attributes)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
