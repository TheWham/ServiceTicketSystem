# Microsoft Entra Management Agent 在完全导入或增量导入期间挂起并出现错误：System.Collections.Generic.KeyNotFoundException

## 概要

本文提供了解决以下问题：Microsoft Entra Management Agent 停止响应出现错误 System.Collections.Generic.KeyNotFoundException 的问题。

*原始产品版本：* Active Directory  
*原始 KB 数：* 3096482

## 现象

在 Microsoft Entra Connector 上运行完全导入或增量导入时，将执行以下操作之一：

- 应用程序日志中记录了以下错误：

  ```
  FIMSynchronizationService Event 6801
  The extensible extension returned an unsupported error.
  The stack trace is:
  "System.Collections.Generic.KeyNotFoundException: The given key was not present in the dictionary.
  at System.Collections.Generic.Dictionary`2.get_Item(TKey key)
  at System.Collections.ObjectModel.KeyedCollection`2.get_Item(TKey key)
  at Microsoft.Azure.ActiveDirectory.Connector.Connector.GetConnectorSpaceEntryChange(SyncObject syncObject)
  at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
  at System.Collections.Generic.List`1.InsertRange(Int32 index, IEnumerable`1 collection)
  at Microsoft.Azure.ActiveDirectory.Connector.Connector.GetImportEntriesCore()
  at Microsoft.Azure.ActiveDirectory.Connector.Connector.GetImportEntries(GetImportEntriesRunStep getImportEntriesRunStep)
  ```
- 看到以下错误消息：

  ```
  DirectorySynchronization Event 109:
  Failure while importing entries from Windows Azure Active Directory. Exception: System.Collections.Generic.KeyNotFoundException: The given key was not present in the dictionary.
  at System.Collections.Generic.Dictionary`2.get_Item(TKey key)
  at System.Collections.ObjectModel.KeyedCollection`2.get_Item(TKey key)
  at Microsoft.Azure.ActiveDirectory.Connector.Connector.GetConnectorSpaceEntryChange(SyncObject syncObject)
  at System.Linq.Enumerable.WhereSelectListIterator`2.MoveNext()
  at System.Collections.Generic.List`1.InsertRange(Int32 index, IEnumerable`1 collection)
  at Microsoft.Azure.ActiveDirectory.Connector.Connector.GetImportEntriesCore()
  at Microsoft.Azure.ActiveDirectory.Connector.Connector.GetImportEntries(GetImportEntriesRunStep getImportEntriesRunStep).
  ```

## 解决方法

若要解决此问题，请选择缺少的对象类型（**设备**）。 为此，请按照下列步骤进行操作：

1. 在 Forefront Identity Manager （FIM） 同步控制台中打开 Microsoft Entra 目录的管理代理。
2. 单击“连接器**”**，然后单击Microsoft **Entra ID**。
3. 在“操作”  窗格中，单击“属性” 。

   注意

   此时将打开“属性”窗口。
4. 在“连接器设计”下**，单击“**选择对象类型**”。**
5. 在 **“选择对象类型** ”窗格中，找到并选择 **设备** 复选框。
6. 单击“确定”三次。

## Status

Microsoft 已经确认这是一个列于“适用范围”部分的 Microsoft 产品问题。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/aad-management-agent-hangs-during-import)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
