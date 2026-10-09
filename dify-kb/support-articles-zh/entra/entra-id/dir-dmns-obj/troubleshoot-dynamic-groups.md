# 对动态组进行故障排除

此故障排除指南可帮助你诊断和解决Microsoft Entra ID 中的动态组的问题。

重要

动态成员身份组更改通常在几个小时内进行处理。 但是，处理可能需要 24 小时以上，具体取决于组数、更改数和规则的复杂性等因素。 有关详细信息，请参阅 [Microsoft Entra ID 中的“了解和管理动态组处理](/zh-cn/entra/identity/users/manage-dynamic-group)”。

## 动态组标识和管理

若要验证组是否为动态组，请参阅 [评估组是否为动态组](#1)。

- **是**：继续下一部分。
- **否**： [使用 Microsoft Entra ID 或其他适用的组创建基本组并添加成员](/zh-cn/azure/active-directory/fundamentals/active-directory-groups-create-azure-portal) 。

### 动态组创建问题

### 参考

创建群组推荐的文章：

- [在 Azure 门户中创建新组并添加成员](/zh-cn/azure/active-directory/fundamentals/active-directory-groups-create-azure-portal)
- [在 PowerShell MSOnline 中创建组](/zh-cn/azure/active-directory/users-groups-roles/groups-settings-v2-cmdlets#create-groups)
- [在 PowerShell 中禁用组创建](/zh-cn/azure/active-directory/users-groups-roles/groups-settings-v2-cmdlets#disable-group-creation-by-your-users)
- [Microsoft Entra 系统管理员角色](/zh-cn/azure/active-directory/users-groups-roles/directory-assign-admin-roles)

创建动态组或规则时出现的常见问题：

- 无法在Azure 门户中创建动态组，或者在 PowerShell 中创建动态组时收到错误。 请参阅 [“无法创建动态组](#4)”。
- 找不到用于创建规则的属性。 请参阅 [“创建动态成员身份规则](#7)”。
- 尝试在 PowerShell 中创建动态组时收到 **“允许的最大组数”** 错误：已达到 15,000 个组，这是租户中动态组的最大限制。 若要创建新的动态组，请先删除现有的动态组。 无法增加最大限制。

### 动态成员身份更新问题

你创建了动态组并配置了规则，但遇到以下常见问题：

组中未显示任何成员，某些用户或设备不会显示在组中，或者组中显示错误的用户或设备。

- 访问 [排查动态成员身份更新问题](#9)。

规则中的现有成员将被移除。

- 此行为在意料之中。 当启用或更改规则或更改属性时，组的现有成员将被删除。 评估规则后返回的用户将作为成员添加到组中。

添加或更改规则后，不会立即看到成员身份更改。

- 成员身份评估作为后台进程定期执行。 此过程的持续时间取决于目录中的用户数，以及由于相应规则而创建的组的大小。 通常，用户数较少的目录在几分钟内就能看到组成员身份变化。 而具有大量用户的目录可能需要 30 分钟或更长时间才能填充信息。
- 检查 [成员身份处理状态](/zh-cn/azure/active-directory/users-groups-roles/groups-create-rule#check-processing-status-for-a-rule) ，确认进程是否已完成。 查看 Azure 门户中组“概述”页面上的最近更新日期，确认页面是否已更新。
- 若要强制处理组，请参阅 [强制立即处理组](#18)。

您收到一个规则处理错误。

- 请参阅 [修复规则处理错误](#19)。

### 动态组删除或还原问题

您在删除组时收到错误。

- 在尝试删除Microsoft Entra ID 中的组之前，请确保 [已删除所有分配的许可证](/zh-cn/azure/active-directory/users-groups-roles/licensing-group-advanced#deleting-a-group-with-an-assigned-license)。 有关组删除的详细信息，请参阅 [“删除组](#21)”。

已还原已删除的组，但未看到任何更新。

- 当删除并还原动态组时，会将视其为一个新组并根据规则重新填充。 此过程可能需要一些时间才能完成，具体取决于租户大小等因素。

## 评估组是否为动态组

确定组是否为动态组：

1. 登录到 [Azure 门户](https://ms.portal.azure.com/)。
2. 在 [“组概述](/zh-cn/azure/active-directory/enterprise-users/groups-create-rule#check-processing-status-for-a-rule) ”选项卡中选择该组，然后检查 **成员身份类型** 是否设置为 **“动态**”。

## 验证动态组成员身份规则

Microsoft Entra ID 提供了验证动态组规则的方法。 在“ **验证规则** ”选项卡上，可以针对示例组成员验证动态规则，以确认该规则是否按预期工作。

创建或更新动态组规则时，可以使用此信息来帮助确定用户或设备是否符合成为组成员的规则条件。 这也有助于解决成员资格不符合预期的情况。

有关详细信息，请参阅 [Microsoft Entra ID 中的“验证动态组成员身份规则”（预览）](/zh-cn/azure/active-directory/users-groups-roles/groups-dynamic-rule-validation)

## 排查动态组创建问题

创建动态组或规则时遇到问题。

### 无法创建动态组

看不到在Azure 门户中创建动态组的选项，或者在 PowerShell 中创建动态组时出错。

1. 确保租户具有相应的许可证。

   - 动态组要求租户具有Microsoft Entra ID **P1 或 P2 Premium 许可证**。 有关详细信息，请查看 [Microsoft Entra ID 许可证计划](https://www.microsoft.com/cloud-platform/azure-active-directory-pricing)
2. 确保创建组的用户具有适当的管理员权限：

   - 确保你有权创建新组。 全局管理员可以在 Azure 门户或访问面板中禁用组创建功能。 可能需要管理员为你创建新的组，或者为你授予适当的权限。
3. 检查是否为要创建的组类型启用了组创建权限。

   - 全局管理员可以管理在 Azure 门户或访问面板中创建的安全或 Office 365 组的组创建权限，方法是设置**用户可以在 Azure 门户中创建安全组**，或者用户可以在 Azure 门户中的“**所有组****常规”（设置）**下的 >。 此设置也适用于动态组。
4. 检查特定用户是否位于可以创建组的用户列表中。

   - 如果拥有Microsoft Entra ID P1 Premium 许可证，全局管理员可以限制组创建以选择一组用户。 应验证你是否具有适当的权限。

### 在 PowerShell 中创建动态组时出现最大组允许的错误

此错误意味着你已达到租户中动态组的最大限制。 检查租户中的组数。 每个租户的最大动态组数为 15,000。

若要创建任何新的动态组，首先需要删除某些现有动态组。 没有办法提高限制。

## 排查动态组规则创建问题

### 找不到用于创建规则的属性

1. 确保用户属性位于 [受支持的属性列表中](/zh-cn/azure/active-directory/active-directory-groups-dynamic-membership-azure-portal#supported-properties)。 如果它们不在列表中，则当前不受支持。
2. 确保设备属性位于 [设备属性列表中](/zh-cn/azure/active-directory/active-directory-groups-dynamic-membership-azure-portal#using-attributes-to-create-rules-for-device-objects)。 如果它们不在列表中，则当前不受支持。 有关详细信息，请访问 [Microsoft Entra ID 中组的动态成员身份规则](/zh-cn/azure/active-directory/enterprise-users/groups-dynamic-membership)。

### 无法创建动态成员身份规则

1. 确保租户具有相应的许可证。 动态组要求租户具有 Microsoft Entra ID P1 Premium 许可证。

   - Microsoft Entra ID **许可证计划**的列表可以在[Microsoft Entra 定价](https://www.microsoft.com/cloud-platform/azure-active-directory-pricing)访问。
   - 企业移动性 + 安全性许可计划可在 [企业移动性+安全性定价选项](https://www.microsoft.com/microsoft-365/enterprise-mobility-security/compare-plans-and-pricing)中访问。
2. 如果找不到内置 **用户属性**，请确保该属性位于 [受支持的属性列表中](/zh-cn/azure/active-directory/active-directory-groups-dynamic-membership-azure-portal#supported-properties)。 如果它不在列表中，则当前不受支持。
3. 如果要查找内置 **设备属性**，请确保该属性位于 [设备属性列表中](/zh-cn/azure/active-directory/active-directory-groups-dynamic-membership-azure-portal#using-attributes-to-create-rules-for-device-objects)。 如果它不在列表中，则当前不受支持。
4. 如果在 Azure 门户中 **的“简单规则** ”下拉列表中找不到该属性，请使用 **高级规则** 来构造规则。

   1. 确保语法准确且属性类型和值都匹配。
   2. 此外，请确保已添加适当的对象前缀以选择属性。

      - 例如： **user.country**、 **device.deviceOSType**。
   3. 了解 [有关如何创建高级规则的指南](/zh-cn/azure/active-directory/active-directory-groups-dynamic-membership-azure-portal#constructing-the-body-of-an-advanced-rule) ，包括受支持的运算符列表和常见规则的示例。
5. 还对动态用户规则使用 [扩展属性](/zh-cn/azure/active-directory/active-directory-groups-dynamic-membership-azure-portal#extension-attributes-and-custom-attributes) 。 创建简单规则时，这些规则将显示在下拉列表中。

   - 可以通过使用 **PowerShell** 查询用户的属性并搜索属性名称，在目录中找到自定义属性名称。 构造高级规则时也可以使用这些属性。
6. 确保创建动态组的用户 **的角色** 是 **公司管理员** 或 **用户管理员**。
7. 请等待群组进行填充。
8. 简单规则生成器最多支持五（5）个表达式。 若要向规则添加五个以上的表达式，必须使用文本框。

## 排查动态成员身份更新问题

你创建了动态组并配置了规则，但遇到以下问题之一：

- 组中未列出任何成员。
- 某些用户或设备未出现在组中。
- 不正确的用户或设备未出现在组中。

### 成员不会按预期添加或删除

1. 检查 [成员身份处理状态](/zh-cn/azure/active-directory/users-groups-roles/groups-create-rule#check-processing-status-for-a-rule) 以确认其是否已完成，并在 Azure 门户中的“组概述”页上检查上次更新的日期，以确认其 up-to-date。
2. 如果成员身份处理状态为**处理错误**并**更新已暂停**，请联系管理员或 PG 团队以使组恢复处理。
3. 按照 [“评估用户或设备的动态成员身份](#11)”中的步骤，验证用户或设备是否满足成员身份规则。
4. 确保处理状态不受“策略不允许添加来宾用户”问题的影响。

   - 如果组是 Office365 组，用户是来宾用户，并且目录设置不允许在租户中添加来宾用户，则无法将来宾用户添加到组中。
   - 一个组中的来宾用户添加错误将阻止同一租户中相同组和其他组的更新。 你可以选择：

     - 通过遵循租户中群组的“管理来宾用户”设置，可以允许添加来宾用户。
     - 通过添加： `(user.userType -eq "member")`更改组规则以排除来宾用户。
5. 如果一切正常，请等待组填充。 根据租户的大小，组在首次填充时或者在规则更改后再次填充时可能需要花费一些时间。 建议等待至少 24 小时，以允许组处理完成。
6. 如果处理状态显示为已完成且问题仍然存在，则可以 [重置组的处理](#18) 以解决任何暂时性系统问题。

   如果处理状态显示为 **正在处理**，请继续等待。

### 评估用户或设备的动态成员身份

若要评估用户或设备是否满足要成为组一部分的规则，请使用 **手动验证**。

#### 手动验证

验证用户或设备属性的值（在 [Azure 门户中](/zh-cn/azure/active-directory/fundamentals/active-directory-users-profile-azure-portal#to-add-or-change-profile-information)或使用规则中的 [PowerShell](/zh-cn/powershell/module/azuread/get-azureaduser) ）。

- 确保有用户满足规则。
- 对于设备，请检查设备属性以确保同步的属性包含预期值。

## 管理 office365 组中的来宾用户设置

首先， [安装 Azure AD PowerShell 模块](/zh-cn/azure/active-directory/users-groups-roles/groups-settings-v2-cmdlets#install-the-azure-ad-powershell-module)

1. 连接到目录。 有关详细信息 [，请访问如何使用 PowerShell 连接到目录](/zh-cn/azure/active-directory/users-groups-roles/groups-settings-v2-cmdlets#connect-to-the-directory) 。
2. 检查目录设置：

   1. 读取租户的目录设置： [读取目录级别的设置](/zh-cn/azure/active-directory/users-groups-roles/groups-settings-cmdlets#read-settings-at-the-directory-level)。
   2. 检查来宾用户设置：如下图所示，如果 **AllowToAddGuests****为 true**，请检查该特定组中的设置。 如果 **AllowToAddGuests** 为 **false**，则无论组级别设置是什么，都无法添加来宾用户。

   ![用于检查 AllowToAddGuests 设置的屏幕截图。](media/troubleshoot-dynamic-groups/allow-to-add-guests.png)
3. 更新租户级别的设置。 若要在租户级别更改来宾用户设置，请访问： [如何使用 PowerShell 更新租户级别的设置](/zh-cn/azure/active-directory/users-groups-roles/groups-settings-cmdlets#update-settings-at-the-directory-level)。
4. 检查组的设置。 若要将来宾用户设置更改为目标值（如果适用），请访问： [如何使用 PowerShell 检查和更新特定组的设置](/zh-cn/azure/active-directory/users-groups-roles/groups-settings-cmdlets#update-settings-for-a-specific-group)

### 从规则中移除现有成员

这是正常现象。 当启用或更改规则或更改属性时，组的现有成员将被删除。 评估规则后返回的用户将作为成员添加到组中。

### 更新规则后，不会立即看到成员身份更改

成员身份评估在后台进程中定期完成。 此过程需要多长时间由多个因素决定。

### 强制立即处理组

重置动态组的处理。 在Azure 门户中，通过更新成员身份规则以在规则中间添加空格来手动触发重新处理。

### 修复规则处理错误

| 规则分析器错误 | 错误用法 | 正确使用 |
| --- | --- | --- |
| 错误：不支持属性 | （user.invalidProperty -eq“Value”） | （user.department -eq「value」） 请确保该属性位于 [支持的属性列表中](/zh-cn/azure/active-directory/users-groups-roles/groups-dynamic-membership#supported-properties)。 |
| 错误：该属性不支持运算符 | （user.accountEnabled -contains true） | (user.accountEnabled -eq 真) 属性类型不支持使用的运算符（在此示例中，不能对布尔类型使用 -contains）。 请对该属性类型使用正确的运算符。 |
| 错误：查询编译错误 | 1. （user.department -eq “Sales”）（user.department -eq “Marketing”） 2. （user.userPrincipalName -match “`*@domain.ext`”） | 1.缺少运算符。 使用 -and 或 -or 来连接两个谓词：（user.department -eq “Sales”） -或 （user.department -eq “Marketing”） 2.与 -match 一起使用的正则表达式出错 （user.userPrincipalName -match “`.*@domain.ext`”） 或：(user.userPrincipalName -match "@domain.ext$") |

## 排查动态组删除或还原问题

在尝试删除Microsoft Entra ID 中的组之前，请确保 [已删除所有分配的许可证](/zh-cn/azure/active-directory/users-groups-roles/licensing-group-advanced#deleting-a-group-with-an-assigned-license) 以避免错误。

（有关组删除的详细信息，请参阅 [“删除组](#21)”。

### 删除组

1. 可以[使用 Microsoft Graph PowerShell 中的 cmdlet`Remove-MgGroup`](/zh-cn/powershell/module/microsoft.graph.groups/remove-mggroup)从目录中删除组。
2. 在尝试删除Microsoft Entra ID 中的组之前，请确保 [已删除所有分配的许可证以避免错误](/zh-cn/azure/active-directory/users-groups-roles/licensing-group-advanced#deleting-a-group-with-an-assigned-license)。

### 还原已删除的组

- 如果删除了某个 Office 365 组，则在永久删除之前只能在 30 天内将其还原。 一旦永久删除，将再也不能还原该组。 若要了解有关还原组的详细信息，请参阅 [还原Microsoft Entra ID 中的已删除Microsoft 365 组](/zh-cn/azure/active-directory/fundamentals/active-directory-groups-restore-azure-portal)。
- 安全组和通讯组不支持此功能。
- 验证您是否有权还原 Office 365 组。 只有全局管理员、用户帐户管理员、Intune 服务管理员或组的所有者才能还原组。

## 相关文章

- [创建动态成员身份规则](/zh-cn/azure/active-directory/users-groups-roles/groups-dynamic-membership#other-properties-and-common-rules)。
- [故障排除组](/zh-cn/azure/active-directory/users-groups-roles/groups-troubleshooting)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/dir-dmns-obj/troubleshoot-dynamic-groups)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
