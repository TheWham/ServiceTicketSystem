# 对具有动态成员身份处理功能的组进行故障排除

在需要重新评估动态组成员身份的 Microsoft Entra ID 中进行更改后，可能会遇到以下任一问题：

- 成员身份更新缓慢
- 意外的组成员变更

这些问题可能是由以下原因引起的：

- 一次意外的成员资格规则变更。
- 重大更改推出。 例如，同时推送到多个设备的更新可能需要重新评估一些组成员身份规则。

本文提供了Microsoft Entra PowerShell 示例，用于暂停和恢复组和管理单元的动态成员身份处理。 暂停动态成员身份处理可以停止规则处理并防止意外的成员身份更新。 恢复动态成员身份处理可以还原正常功能。

重要

动态成员身份组更改通常在几个小时内处理。 但是，处理可能需要 24 小时以上，具体取决于租户大小、组大小、属性更改数、规则复杂性和运算符选择（如使用 `CONTAINS`、 `MATCH`或 `MemberOf`）。 有关详细信息，请参阅 [Microsoft Entra ID 中的“了解和管理动态组处理](/zh-cn/entra/identity/users/manage-dynamic-group)”。

## 获取暂停和恢复动态成员身份处理示例

PowerShell 示例在 Microsoft Learn 上发布。 从 [PowerShell 示例开始进行动态成员身份处理](/zh-cn/entra/identity/users/groups-dynamic-membership-powershell-samples)。

若要运行示例，请确保满足以下先决条件：

- PowerShell 5.1 （x64） 或更高版本。
- [Microsoft Graph PowerShell 模块](/zh-cn/powershell/microsoftgraph/installation)。
- 一个已登录的帐户，可以管理你所针对的集合。 群组阶段需要 [Groups Administrator](/zh-cn/entra/identity/role-based-access-control/permissions-reference#groups-administrator) Microsoft Entra 角色和 `Group.ReadWrite.All` Microsoft Graph 权限范围。 管理单元阶段需要 [特权角色管理员](/zh-cn/entra/identity/role-based-access-control/permissions-reference#privileged-role-administrator) Microsoft Entra 角色和 `AdministrativeUnit.ReadWrite.All` 范围。

## 动态成员身份管理示例

我们提供了五个 PowerShell 示例来管理组和管理单元的动态成员身份处理：

- [暂停具有动态成员身份的所有组和管理单元](/zh-cn/entra/identity/users/scripts/powershell-pause-all-dynamic-membership)：暂停租户中具有动态成员身份规则的每个组和管理单元。
- [暂停具有动态成员身份的特定组和管理单元](/zh-cn/entra/identity/users/scripts/powershell-pause-specific-dynamic-membership)：仅暂停你提供的 ID 的组和管理单元。
- [暂停除指定项外的所有具有动态成员身份的组和管理单元](/zh-cn/entra/identity/users/scripts/powershell-pause-all-except-dynamic-membership)：暂停所有具有动态成员身份的组和管理单元，但不包括你排除的 ID。
- [恢复具有动态成员身份的特定关键组和管理单元](/zh-cn/entra/identity/users/scripts/powershell-resume-specific-critical-dynamic-membership)：恢复对指定的关键组和管理单元的处理。
- [以批量方式恢复具有动态成员身份的非关键组和管理单元](/zh-cn/entra/identity/users/scripts/powershell-resume-noncritical-dynamic-membership)：恢复对暂停的非关键组和管理单元的处理，每个运行最多 100 个。

每个示例分两个阶段进行：先处理组，再处理管理单元。 在每个阶段开始时，脚本会要求确认。 可以运行组阶段、管理单元阶段或两者。

重要

在生产环境中进行任何更改之前，请先验证测试环境中的所有步骤。

## FAQ

### 何时使用“暂停所有组和管理单元”示例

如果你怀疑发生了非预期更改，或者遇到影响许多组或管理单元的大范围动态成员身份更新延迟，请使用 [暂停具有动态成员身份的所有组和管理单元](/zh-cn/entra/identity/users/scripts/powershell-pause-all-dynamic-membership) 示例。

### 何时使用特定暂停示例或“全部暂停（部分除外）”示例

如果您必须暂停特定组或管理单元的动态成员身份处理，或者暂停除某些动态成员身份集合之外的所有动态成员身份集合的处理，请使用 [pause-specific](/zh-cn/entra/identity/users/scripts/powershell-pause-specific-dynamic-membership) 或 [pause-all-except](/zh-cn/entra/identity/users/scripts/powershell-pause-all-except-dynamic-membership) 示例。

### 如何判断何时可以安全地恢复动态成员资格处理

目前，Microsoft Entra 不提供用于监视动态成员身份处理状态的监控能力。 建议在恢复处理之前至少等待 12 小时，以允许服务从任何问题中恢复。

备注

只有在您等待了建议的 12 小时后，Microsoft Entra 支持团队才能帮助您恢复动态成员身份处理。

### 如何恢复动态成员身份处理

运行 [resume-specific-critical](/zh-cn/entra/identity/users/scripts/powershell-resume-specific-critical-dynamic-membership) 示例，以便在至少等待 12 小时后恢复特定关键组或管理单元的规则处理。 若要防止再次发生广泛延迟，请首先恢复关键集合的处理，然后使用 [恢复非关键](/zh-cn/entra/identity/users/scripts/powershell-resume-noncritical-dynamic-membership) 示例以批处理方式恢复剩余的非关键集合的处理。

## 相关内容

- [用于动态成员身份处理的 PowerShell 示例](/zh-cn/entra/identity/users/groups-dynamic-membership-powershell-samples)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/dir-dmns-obj/troubleshoot-dynamic-group-processing)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
