# 在 Microsoft Entra Connect 中的增量导入期间出现“超出大小限制 - 错误代码0x4”错误消息

## 概要

本文介绍如何排查“超出大小限制 - 错误代码0x4”错误消息，该错误消息发生在从 Microsoft Entra Connect 中的本地 Active Directory增量导入步骤中。

## 现象

在 Synchronization Service Manager 应用中，[本地 Active Directory**连接器**中的增量导入](/zh-cn/azure/active-directory/hybrid/connect/how-to-connect-sync-service-manager-ui-operations)步骤失败。 “**连接日志**”对话框显示已删除**的连接**状态、**“超出**大小限制”错误和0x4**错误代码**：

[![Synchronization Service Manager 应用的“操作”选项卡的屏幕截图。“连接日志”对话框显示已删除的连接事件。](media/size-limit-exceeded/synchronization-service-manager-dropped-connection.png)](media/size-limit-exceeded/synchronization-service-manager-dropped-connection.png#lightbox)

在应用程序日志中，记录错误事件 ID 6050，如以下示例所示：

```
Log Name:      Application
Source:        ADSync
Date:          5/12/2023 7:34:38 AM
Event ID:      6050
Task Category: Management Agent Run Profile
Level:         Error
Keywords:      Classic
User:          N/A
Computer:      AADConnect.Contoso.com
Description:
The management agent "Contoso.com" failed on run profile "Delta Import" because of connectivity issues.
 
 Additional Information
 Discovery Errors       : "0"
 Synchronization Errors : "0"
 Metaverse Retry Errors : "0"
 Export Errors          : "0"
 Warnings               : "0"
 
 User Action
 View the management agent run history for details.
```

## 原因

默认情况下，在 Microsoft Entra ID 中创建轻型目录访问协议（LDAP）搜索或查询时，该目录可以返回不超过 1,000 条记录。 根据安全设计，这是 Active Directory 的默认行为。 1,000 条记录限制旨在防止对 LDAP 查询进行分布式拒绝服务（DDoS）攻击。 如果最近从 Active Directory 回收站同时还原了大量对象，则可能会出现此问题。 还原过程可能会导致增量导入查询超过记录限制。

## 解决方案 1：在 AD DS 连接器上运行完全导入

此问题的最简单解决方法是在 Active Directory 域服务 （AD DS） 连接器上手动运行完整导入（而不是增量导入）。 执行以下步骤：

1. 选择“开始”，然后搜索并选择“**同步服务管理器**”。
2. 在 **“同步服务管理器** ”窗口中，选择 **未连接的本地 AD 连接器的增量导入** 步骤。 查找显示 **已停止连接** 状态的增量导入步骤。
3. 选择 `Ctrl`+`F5`，或右键单击所选内容，然后选择“**运行”。**
4. 在 **“运行连接器** ”对话框中，选择“ **完全导入** 运行配置文件”，然后选择“ **确定**”。

完全导入完成后，打开 PowerShell 控制台，并运行 `Start-ADSyncSyncCycle` cmdlet 以启动正常的增量同步周期。 Microsoft Entra Connect Sync： Scheduler [中](/zh-cn/azure/active-directory/hybrid/connect/how-to-connect-sync-feature-scheduler)介绍了此过程。

## 解决方案 2：暂时增加记录限制

如果不想在 AD DS 连接器上运行完全导入，可以暂时更改配置，以便 LDAP 搜索可以在增量同步期间返回更多记录。

若要增加 1,000 条记录限制，请增加最大页面大小 （`MaxPageSize`） 设置以适应增量导入步骤返回的对象数。 例如，如果还原了具有 5,000 个用户的组织单位（OU），建议暂时增加到 `MaxPageSize` 值 5,000。 然后，解决Microsoft Entra Connect 问题后，还原 `MaxPageSize` 到默认值 1,000。

若要更改 `MaxPageSize` 设置，请运行 [Ntdsutil](/zh-cn/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/cc753343(v=ws.11)) 命令，如以下过程所示。 有关详细信息 `MaxPageSize`，请参阅 [LDAP 管理限制](../../../windows-server/identity/view-set-ldap-policy-using-ntdsutil#ldap-administration-limits)。

重要

请认真遵循本部分所述的步骤。 如果修改默认 AD 配置不正确，则可能会出现严重问题。 解决问题后，可以还原默认值。

1. 选择“开始”，输入*命令提示符*，然后选择“**以管理员**身份运行”。
2. 在命令提示符下，输入 `ntdsutil` 以启动 Ntdsutil 控制台会话。
3. [在 Active Directory 中使用Ntdsutil.exe](../../../windows-server/identity/view-set-ldap-policy-using-ntdsutil)文章查看和设置 LDAP 策略时，请按照“查看当前策略设置[”部分中的说明](../../../windows-server/identity/view-set-ldap-policy-using-ntdsutil#view-current-policy-settings)了解策略设置当前是什么。
4. 若要更改最大页面大小，请输入 `set MaxPageSize to <new-maximum-page-size-value>`。
5. 输入 `commit changes` 以应用新值。
6. 若要退出 Ntdsutil 会话，请输入 `quit` 两次。

进行配置更改后，打开 PowerShell 控制台，然后运行 `Start-ADSyncSyncCycle` cmdlet 以启动正常的增量同步周期。 Microsoft Entra Connect Sync： Scheduler [中](/zh-cn/azure/active-directory/hybrid/connect/how-to-connect-sync-feature-scheduler)介绍了此过程。 现在，Active Directory 将返回大量记录，并且它应该能够向 Microsoft Entra Connect 提供完整的增量响应。

增量同步成功完成后，重复此过程，将 `MaxPageSize` 设置还原到其原始值（1,000）。

## 参考

[LDAP 策略](/zh-cn/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/cc770976(v=ws.11))

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/size-limit-exceeded)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
