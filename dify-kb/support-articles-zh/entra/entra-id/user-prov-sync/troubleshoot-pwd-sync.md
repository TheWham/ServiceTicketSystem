# 如何使用 Microsoft Entra Connect 排查密码同步问题

## 概要

本文可帮助你排查将密码从本地环境同步到使用 Microsoft Entra Connect [Microsoft Entra ID](/zh-cn/azure/active-directory/hybrid/whatis-azure-ad-connect) 时可能会遇到的常见问题。

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2855271

备注

本文有帮助吗? 你的输入对我们很重要。 请使用此页上的 **“反馈** ”按钮告诉我们本文为你工作得有多好，或者我们如何改进它。

## 开始故障排除之前

在执行故障排除步骤之前，请确保已安装 [最新版本的 Microsoft Entra Connect](/zh-cn/azure/active-directory/hybrid/how-to-connect-install-roadmap#install-azure-ad-connect) 。

此外，请确保目录同步处于正常状态。 有关详细信息，请参阅[使用 Microsoft Entra Connect 同步对对象同步进行故障排除](/zh-cn/azure/active-directory/hybrid/tshoot-connect-objectsync)。

## 某些用户无法登录到 Microsoft 365、Microsoft Entra 或 Microsoft Intune

在此方案中，大多数用户的密码似乎正在同步。 但是，某些用户的密码似乎未同步。下面是用户无法登录到 Microsoft 云服务（如 Microsoft 365、Entra 或 Intune）的方案。

### 方案 1：为用户帐户选中了“用户下次登录时必须更改密码”复选框

若要解决此问题，请按照下列步骤操作：

1. 请执行以下一项操作：

   - 在Active Directory 用户和计算机的用户帐户属性中，清除“**用户必须在下次登录**时更改密码”复选框。
   - 让用户更改其本地用户帐户密码。
   - 在 [Microsoft Entra ID 中启用 ForcePasswordChangeOnLogOn](/zh-cn/azure/active-directory/hybrid/how-to-connect-password-hash-synchronization#synchronizing-temporary-passwords-and-force-password-change-on-next-logon) 功能。
2. 等待几分钟，更改才能在本地 Active Directory域服务（AD DS）和Microsoft Entra ID 之间同步。

### 方案 2：用户在云服务门户中更改了其密码

若要解决此问题，请按照下列步骤操作：

1. 让用户更改其本地用户帐户密码。
2. 等待几分钟，更改在本地 AD DS 与 Microsoft Entra ID 之间同步。

若要更改云服务中的密码，并让 Microsoft Entra Connect 更新相应的本地用户帐户密码，请启用 [密码写回](/zh-cn/entra/identity/authentication/tutorial-enable-sspr-writeback)。

### 方案 3：某些用户似乎未同步到 Microsoft Entra ID

可能的原因有重复的用户名或电子邮件地址。

若要解决此问题，请使用 IdFix DirSync 错误修正工具（IdFix）帮助识别本地 AD DS 中潜在的对象相关问题。 可以在以下Microsoft网站安装 IdFix： [IdFix DirSync 错误修正工具](https://github.com/microsoft/idfix)

有关如何排查此问题的详细信息，请参阅 [使用 Azure Active Directory 同步工具时一个或多个对象不会同步](objects-dont-sync-ad-sync-tool)

### 方案 4：在包含和排除的同步范围之间移动用户

在此方案中，用户将移动到一个范围，该范围现在允许用户同步。 可能是在为域、组织单位或属性设置筛选时。

若要解决此问题，请参阅 **“如何执行初始同步** ”部分。

### 方案 5：用户无法使用新密码登录，但可以使用旧密码登录

在此方案中，你将使用 Microsoft Entra Connect 和密码同步。 禁用目录同步或密码同步后，用户无法使用新密码登录。 但是，他们的旧密码仍然有效。

若要解决此问题，请重新启用目录同步和密码同步。 为此，请启动Microsoft Entra Connect 配置向导，选择“ **配置** 和 **自定义同步”选项**，然后继续通过屏幕，直到看到启用密码同步的选项。

### 方案 6：用户无法使用其密码登录

在此方案中，密码哈希不会成功同步到 Microsoft Entra ID。 如果用户帐户是在低于 Windows Server 2003 的 Windows Server 版本的本地 AD DS 中创建的，该帐户没有密码哈希。

## 目录同步正在运行，但所有用户的密码不会同步

在此方案中，所有用户的密码似乎未同步。如果以下条件之一为 true，则通常会发生此情况：

- 未选中配置完成后**启动同步过程的复选框**。
- Entra Connect 服务器处于过渡模式。
- 密码同步已禁用。
- 尚未完成完整目录同步。

重要

在完整目录同步完成之前，密码同步不会启动。

若要解决此问题，请先确保启用密码同步。 为此，请启动Microsoft Entra Connect 配置向导，选择“ **配置** 和 **自定义同步”选项**，然后继续通过屏幕，直到看到启用密码同步的选项。

启用密码同步后，必须等待完整密码同步完成。 检查 Windows [事件查看器日志](troubleshoot-pwd-sync#event-id-messages-in-event-viewer)以监视密码同步过程。

## 排查未同步其密码的用户的问题

若要解决此问题，请参阅 [使用 Microsoft Entra Connect 同步排查密码哈希同步问题](/zh-cn/azure/active-directory/hybrid/tshoot-connect-password-hash-synchronization#one-object-is-not-synchronizing-passwords-troubleshoot-by-using-the-troubleshooting-task)

## 正在从单一登录（SSO）解决方案更改为密码同步

若要解决此问题，请参阅 [如何从单一登录切换到密码同步](/zh-cn/archive/technet-wiki/17857.dirsync-how-to-switch-from-single-sign-on-to-password-sync)。

## 事件查看器中的事件 ID 消息

下表列出了与密码同步相关的应用程序日志中的事件 ID 消息。

### 信息性（无需执行任何作）

| 事件 ID | 说明 | 原因 |
| --- | --- | --- |
| 6:22 | 域的完整密码哈希同步已完成：contoso.local | 完整密码同步周期完成从本地 AD DS 域检索最近的密码。 |
| 6:23 | 为林完成的完整密码哈希同步：contoso.local | 完整密码同步周期完成从本地 AD DS 林检索最近的密码。 |
| 6:50 | 预配凭据批处理开始。 计数：1 | 密码同步开始从本地 AD DS 检索更新的密码。 |
| 下午 6：02：51 | 预配凭据批处理结束。 计数：1 | 密码同步完成从本地 AD DS 检索更新的密码。 |
| 653 | 预配凭据 ping 启动。 | 密码同步开始通知Microsoft Entra ID，没有要同步的密码。 如果本地 AD DS 中未更新任何密码，则每隔 30 分钟发生一次。 |
| 下午 6：02：54 | 预配凭据 ping 端。 | 密码同步完成，告知Microsoft Entra ID 没有要同步的密码。 如果未在本地 AD DS 中更新任何密码，则每隔 30 分钟发生一次。 |
| 656 | 密码更改请求 - 定位点：H552hI9GwEykZwosf74JeOQ=，Dn： CN=Viola Hanson，OU=Cloud Objects，DC=contoso，DC=local，更改日期：2013/05/01/16：34：08 | 密码同步指示检测到密码更改，并尝试将其同步到Microsoft Entra ID。 它标识密码已更改并将同步的用户或用户。 每个批次至少包含一个用户和最多 50 个用户。 |
| 657 | 密码更改结果 - 定位点：eX5b50Rf+UizRIMe2CA/tg==，Dn： CN=Viola Hanson，OU=Cloud Objects，DC=contoso，DC=local，Result： Success。 | 已成功同步其密码的用户。 |
| 657 | 密码更改结果 - 定位点：eX5b50Rf+UizRIMe2CA/tg==，Dn： CN=Viola Hanson，OU=Cloud Objects，DC=contoso，DC=local，Result： Failed。 | 密码未同步的用户。 |

### 信息性 （可能需要作）

| 事件 ID | 说明 | 原因 | 详细信息 |
| --- | --- | --- | --- |
| 0 | 以下密码更改无法同步，并已计划重试。  DN = CN=Eli McLean，OU=Cloud Objects，DC=contoso，DC=local | 未同步其密码的用户或用户 | [配置目录同步](/zh-cn/azure/active-directory/hybrid/whatis-hybrid-identity#bkmk_configuretool)    [使用 Azure Active Directory 同步工具时，一个或多个对象不会同步](objects-dont-sync-ad-sync-tool) |
| 1:15 | 对 Windows Azure Active Directory 的访问被拒绝。 请与技术支持部门联系。 | Microsoft Entra 凭据是通过 Forefront Identity Manager （FIM） 更新的。 | 再次运行Microsoft Entra 配置向导。 在 FIM 中更新 Microsoft Entra 凭据后，请参阅 [密码哈希同步停止工作](pwd-hash-sync-stop-work-fim) |
| 657 | 密码更改结果 - 定位点：B0H+OD3LM0GEnYODwdPhpg==，结果： 失败，扩展错误： | 未同步其密码的用户或用户 | [配置目录同步](/zh-cn/azure/active-directory/hybrid/whatis-hybrid-identity#bkmk_configuretool)    [使用 Azure Active Directory 同步工具时，一个或多个对象不会同步](objects-dont-sync-ad-sync-tool) |

### 错误（需要作）

| 事件 ID | 说明 | 原因 | 详细信息 |
| --- | --- | --- | --- |
| 0 | 用户名或密码不正确。 验证用户名，然后再次键入密码。 | Microsoft Entra 凭据是通过 Forefront Identity Manager （FIM） 更新的。 | 再次运行Microsoft Entra 配置向导。 在 FIM 中更新 Microsoft Entra 凭据后，请参阅 [密码哈希同步停止工作](pwd-hash-sync-stop-work-fim) |
| 6:11 | 域的密码同步失败： `Contoso.com`。  Microsoft.Online.PasswordSynchronization.SynchronizationManagerException：恢复任务失败。 >--- Microsoft.Online.PasswordSynchronization.DirectoryReplicationServices.DrsException： RPC 错误 8439：为此复制作指定的可分辨名称无效。 调用\_IDL\_DRSGetNCChanges时出错。 | Windows Server 2003 域控制器意外处理某些方案。 | [Microsoft Entra ID 的密码哈希同步停止工作，并记录事件 ID 611](pwd-hash-sync-stops-work) |
| 6:11 | 域的密码同步失败： `Contoso.com`。  Microsoft.Online.PasswordSynchronization.DirectoryReplicationServices.DrsException： RPC 错误 8593：目录服务无法执行请求的作，因为所涉及的服务器属于不同的复制纪元（这通常与正在进行的域重命名相关）。 | 这是 Azure Active Directory 同步工具内部版本 1.0.6455.0807 中已修复的已知问题。 | 若要解决此问题，请更新到最新版本的 Azure Active Directory 同步工具。 |
| 6:11 | 域的密码同步失败： `Contoso.com`  System.ArgumentOutOfRangeException：不是有效的 Win32 | 这是 Azure Active Directory 同步工具内部版本 1.0.6455.0807 中已修复的已知问题。 | 若要解决此问题，请更新到最新版本的 Azure Active Directory 同步工具。 |
| 6:11 | 域的密码同步失败： `Contoso.com`。  System.ArgumentException：已添加具有相同键的项。 | 这是 Azure Active Directory 同步工具内部版本 1.0.6455.0807 中已修复的已知问题。 | 若要解决此问题，请更新到最新版本的 Azure Active Directory 同步工具。 |
| 652 | 凭据预配批处理失败。 错误：Microsoft.Online.Coexistence.ProvisionException：发生错误。 错误代码：90。 错误说明：尚未为此公司激活密码同步。 跟踪 ID：07e93e8a-cf2d-4f67-9e95-53169c4875e0 服务器名称：BL2GR1BBA003。 >--- System.ServiceModel.FaultException1[Microsoft.Online.Coexistence.Schema.AdminWebServiceFault]：尚未为此公司激活密码同步。 （错误详细信息等于 Microsoft.Online.Coexistence.Schema.AdminWebServiceFault）。 | 从本地 AD DS 检索更新的密码时，密码同步失败。 | [配置目录同步](/zh-cn/azure/active-directory/hybrid/whatis-hybrid-identity#bkmk_configuretool)    [使用 Azure Active Directory 同步工具时，一个或多个对象不会同步](objects-dont-sync-ad-sync-tool) |
| 652 | 凭据预配批处理失败。 错误：Microsoft.Online.共存。 ProvisionRetryException：发生错误。 错误代码：81。 错误说明：Windows Azure Active Directory 当前正忙。 将自动重试此操作。 | 这是 Azure Active Directory 同步工具内部版本 1.0.6455.0807 中已修复的已知问题 | 若要解决此问题，请更新到最新版本的 Azure Active Directory 同步工具。 |
| 655 | 凭据预配 ping 失败。 错误：Microsoft.Online.Coexistence.ProvisionException：发生错误。 错误代码：90。 错误说明：尚未为此公司激活密码同步。 跟踪 ID：0744fa31-1d9b-453a-83d8-c2555d843802 服务器名称：BL2GR1BBA005。 >--- System.ServiceModel.FaultException1[Microsoft.Online.Coexistence.Schema.AdminWebServiceFault]：尚未为此公司激活密码同步。 （错误详细信息等于 Microsoft.Online.Coexistence.Schema.AdminWebServiceFault）。 | 密码同步无法通知Microsoft Entra ID，没有要同步的密码。 每 30 分钟发生一次。 | [配置目录同步](/zh-cn/azure/active-directory/hybrid/whatis-hybrid-identity#bkmk_configuretool)    [使用 Azure Active Directory 同步工具时，一个或多个对象未同步](objects-dont-sync-ad-sync-tool) |
| 655 | 用户名或密码不正确。 验证用户名，然后再次键入密码。 | Microsoft Entra 凭据是通过 FIM 更新的。 | 再次运行Microsoft Entra 配置向导。 请参阅以下Microsoft知识库文章： [密码哈希同步在 FIM 中更新 Microsoft Entra 凭据后停止工作](pwd-hash-sync-stop-work-fim) |
| 6900 | 服务器在处理密码更改通知时遇到意外的错误：  用户名或密码不正确”的错误。 验证用户名，然后再次键入密码。 | Microsoft Entra 凭据是通过 FIM 更新的。 | 再次运行Microsoft Entra 配置向导。 请参阅以下Microsoft知识库文章： [密码哈希同步在 FIM 中更新 Microsoft Entra 凭据后停止工作](pwd-hash-sync-stop-work-fim) |
| 6900 | 服务器在处理密码更改通知时遇到意外的错误：  “发生错误。 错误代码：90。 错误说明：尚未为此公司激活密码同步 | 未为组织启用密码同步。 | 请参阅以下Microsoft知识库文章：[用户密码未同步，并且“尚未为此公司激活密码”错误记录事件查看器](/zh-cn/office365/troubleshoot/active-directory/password-synchronization-not-activated) |

## 详细信息

### 如何执行初始同步

若要执行完全同步，请根据所使用的Microsoft Entra Connect 执行以下步骤。

1. 在安装 Microsoft Entra Connect 的服务器上，打开 PowerShell，然后导入 ADSync 模块：

```
   Import-Module ADSync
```

2. 运行以下命令以启动初始同步周期：

```
Start-ADSyncSyncCycle -PolicyType Initial
```

### 如何执行完整密码同步

若要执行完整密码同步，请运行此页上的脚本： [Azure AD Sync：如何使用 PowerShell 触发完全密码同步](/zh-cn/archive/technet-wiki/28433.azure-ad-sync-how-to-use-powershell-to-trigger-a-full-password-sync)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/troubleshoot-pwd-sync)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
