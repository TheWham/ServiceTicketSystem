# Microsoft Entra ID 的密码哈希同步停止工作，并记录事件 ID 611

## 概要

本文提供有关解决 Microsoft Entra ID 的密码哈希同步功能停止正常工作并记录事件 ID `611` 的指南。

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2867278

## 现象

Microsoft Entra ID 的密码哈希同步在几天后停止工作。 此外，在事件查看器中，应用程序日志中记录了以下事件 ID 611 错误：

> 域的密码同步失败： `Contoso.com`。

## 解决方法

安装最新版本的 Microsoft Entra Synchronization 工具。 有关详细信息，请参阅 [安装或升级目录同步工具](/zh-cn/azure/active-directory/hybrid/how-to-dirsync-upgrade-get-started)。

## 详细信息

对于事件 ID 611，可能会看到以下一个或多个错误详细信息。

| 说明 | 原因 | 详细信息 |
| --- | --- | --- |
| Microsoft.Online.PasswordSynchronization。 SynchronizationManagerException：恢复任务失败。 >--- Microsoft.Online.PasswordSynchronization。 DirectoryReplicationServices.DrsException： RPC 错误 8439：为此复制操作指定的可分辨名称无效。 调用时出错 `_IDL_DRSGetNCChanges`。 | Windows Server 2003 域控制器意外处理某些方案。 | 更新到最新版本的 Microsoft Entra Connect 以解决此问题。 |
| Microsoft.Online.PasswordSynchronization。 DirectoryReplicationServices.DrsException： RPC 错误 8593：目录服务无法执行请求的操作，因为所涉及的服务器属于不同的复制纪元（这与正在进行的域重命名相关）。 | 这是 Azure Active Directory 同步工具内部版本 1.0.6455.0807 中已修复的已知问题。 | 更新到最新版本的 Microsoft Entra Connect 以解决此问题。 |
| System.ArgumentOutOfRangeException：不是有效的 Win32 FileTime。 | 这是 Azure Active Directory 同步工具内部版本 1.0.6455.0807 中已修复的已知问题。 | 更新到最新版本的 Microsoft Entra Connect 以解决此问题。 |
| System.ArgumentException：已添加具有相同键的项。 | 这是 Azure Active Directory 同步工具内部版本 1.0.6455.0807 中已修复的已知问题。 | 更新到最新版本的 Microsoft Entra 工具以解决此问题。 |
| 域的密码同步失败： `Contoso.com`。 详细信息： Microsoft.Online.PasswordSynchronization。 DirectoryReplicationServices.DrsException： RPC 错误 8453：复制访问被拒绝。 调用时出错 `_IDL_DRSGetNCChanges`。  at Microsoft.Online.PasswordSynchronization。 DirectoryReplicationServices.DrsRpcConnection.OnGetChanges（ReplicationState syncState）  at Microsoft.Online.PasswordSynchronization。 DirectoryReplicationServices.DrsConnection.GetChanges（ReplicationState replicationState）  at Microsoft.Online.PasswordSynchronization。 RetryUtility.ExecuteWithRetry[T]（Func`1 operation, Func`1 shouldAbort， RetryPolicyHandler retryPolicy）  at Microsoft.Online.PasswordSynchronization。 DeltaSynchronizationTask.SynchronizeCredentialsToCloud（）  at Microsoft.Online.PasswordSynchronization。 PasswordSynchronizationTask.SynchronizeSecrets（）  at Microsoft.Online.PasswordSynchronization。 SynchronizationExecutionContext.SynchronizeDomain（）  at Microsoft.Online.PasswordSynchronization。 SynchronizationManager.SynchronizeDomain（SynchronizationExecutionContext syncExecutionContext）。 | AD DS 连接器帐户缺少对 AD 的以下扩展权限：   - 复制目录更改 - 复制目录更改全部 | 更新到最新版本的 Microsoft Entra Connect，并按照文章“[Microsoft Entra Connect： 配置 AD DS 连接器帐户权限”，了解如何添加正确的 Active Directory 权限](/zh-cn/azure/active-directory/hybrid/how-to-connect-configure-ad-ds-connector-account)。 |

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/pwd-hash-sync-stops-work)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
