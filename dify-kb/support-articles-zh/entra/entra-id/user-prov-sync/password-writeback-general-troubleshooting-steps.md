# 一般密码写回故障排除步骤

本文介绍解决密码写回问题的常规故障排除步骤。 如果必须查阅其他内容来解释更具体的问题，则这些步骤是启动该过程的好方法。

## 专注于确切的故障方案

应一致地说明如何重现或测试密码问题。 确切了解故障方案是什么，并了解重现步骤。 由于密码重置和密码更改是两个不同的操作，因此请专注于一个操作，并为该操作使用相同的步骤来重现问题。 操作之间的差异如下。

| 操作 | 特征 |
| --- | --- |
| 密码重置 | 用户或管理员不知道或不提供当前密码。 |
| 密码更改 | 只有用户才能启动密码更改。 用户必须先输入其当前密码，然后才能指定新密码。 |

## 对比工作和非工作用户

对于一个用户，操作是否失败，但对另一个用户成功？ 在这种情况下，请尝试确定工作和非工作用户之间的差异。 可以使用以下步骤：

1. 通过运行 [Ldifde](/zh-cn/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/cc731033(v=ws.11)) 命令或 [Get-ADUser](/zh-cn/powershell/module/activedirectory/get-aduser) PowerShell cmdlet 获取有关某些 Active Directory 用户的信息。
2. 在 Microsoft Graph PowerShell 中运行[用户命令，以获取有关 Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview) [中的](/zh-cn/powershell/microsoftgraph/find-mg-graph-command)这些用户的信息。
3. 比较 Active Directory 和 Microsoft Graph PowerShell 有关这两个用户脱机的信息，尤其是在以下方面：

   - 管理员角色和组
   - 组织单位放置
   - 上次同步对象和密码的时间
   - 其他差异

   排查问题时，请保持此信息方便。

## 使用相同的域控制器

每次测试或更改时，请尝试使用同一域控制器。 若要控制要联系哪个域控制器以执行密码写回操作，请在 Active Directory 连接器中设置单个首选域控制器，然后重启 ADSync 服务。 将首选域控制器更改为最近的域控制器，或使用拥有主域控制器（PDC）模拟器角色的域控制器。

若要设置首选域控制器，请执行以下步骤：

1. 打开“同步服务管理器”。 为此，请选择“开始”，输入**Microsoft Entra ID**，选择*Microsoft Entra Connect* 组，然后选择“**同步服务**”。
2. **选择“连接器**”选项卡，然后选择适用的 Active Directory 连接器。 在**“操作**”窗格中，选择“属性**”**以打开**“属性**”对话框。
3. 在 **“连接器设计器** ”窗格中，选择“ **配置目录分区**”。 在 **“配置目录分区** ”窗格中，从列表中选择目录分区。
4. 在 **域控制器连接设置** 组中，选中 **“仅使用首选域控制器** ”复选框。 然后选择“**配置**”。
5. 在 **“配置首选 DC** ”对话框中进行相应的更改。

根据问题，它实际上可能有助于尝试不同的域控制器。 然后，可以确定问题是可以隔离到特定的域控制器上，还是在任何域控制器上发生。

此外，使用Active Directory 用户和计算机管理单元时，请将连接的域控制器更改为用于 Microsoft Entra Connect 的域控制器。 执行以下步骤：

1. 打开“Active Directory 用户和计算机”管理单元。 为此，请选择“开始**”**，搜索 *dsa.msc*，然后按 Enter。
2. 在导航窗格中，右键单击域名，然后选择“ **更改域控制器** ”菜单项。
3. 在 **“更改目录服务器** ”对话框中，选择“ **此域控制器”或“AD LDS 实例** ”选项。
4. 在域控制器列表中，选择与为 Microsoft Entra Connect 选择的域控制器匹配，然后选择“ **确定**”。

## 暂时放宽本地 Active Directory 密码策略

若要排查密码写回操作问题，建议暂时修改本地 [Active Directory 密码策略](/zh-cn/windows/security/threat-protection/security-policy-settings/password-policy)。 将 [最短密码期限](/zh-cn/windows/security/threat-protection/security-policy-settings/minimum-password-age) 设置为零，以允许用户连续多次更改其密码。 如果需要 [密码复杂性](/zh-cn/windows/security/threat-protection/security-policy-settings/password-must-meet-complexity-requirements)，请使用大写字母、小写字母和数字的组合。 由于 [密码历史记录通常强制](/zh-cn/windows/security/threat-protection/security-policy-settings/enforce-password-history) 使用默认的 24 个记住的密码，因此在每次重置或更改尝试时始终使用另一个密码。 例如，每次重置或更改时，都会递增整数后缀（1、2、3 等）。

## 使用事件查看器检查应用程序事件

这些特定密码写回问题的故障排除文章包含许多应用程序事件示例，这些示例提供有关问题的详细信息。 这些示例显示，事件查看器管理单元（*Eventvwr.msc*）是排查密码写回问题最有效的 Windows 工具。

## 标识 AD DS 连接器的确切帐户名称

重新检查 Active Directory 域 连接器的当前帐户的名称。 确保此帐户的名称与 Microsoft Entra Connect 服务器使用的帐户相同。 若要查找此帐户名称，请参阅 [“标识 AD DS 连接器帐户](password-writeback-access-rights-permissions#identify-the-ad-ds-connector-account)”。

## 了解支持或不受支持的写回操作

若要查看受支持和不支持的密码写回操作列表，请参阅[自助服务密码重置写回在 Microsoft Entra ID 中的工作原理？](/zh-cn/azure/active-directory/authentication/concept-sspr-writeback)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/password-writeback-general-troubleshooting-steps)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
