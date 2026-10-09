# 解决 SQLLocalDB 中的模型数据库损坏问题

## 概要

本文介绍 SQLLocalDB 实用工具中的 [一个已知问题，该实用工具](/zh-cn/sql/tools/sqllocaldb-utility) 可能会由于数据库损坏 `Model` 而阻止 ADSync 服务启动。 此问题主要影响 Microsoft Entra Connect 2。*Microsoft SQL Server 2019 LocalDB 上运行的 x* 服务器。

此问题由 SQL Server 备份逻辑中的 bug 导致，该错误在 SQL Server `Model` 数据库起始页中创建不一致的状态。 备份发生后，数据库 `Model` 将设置为 `FULL` 恢复模式（`dbi_status` == 0x40010000），数据库 `dbi_dbbackupLSN` 备份的（日志序列号（LSN）设置为指向日志文件的值。 但是，由 `Master` 数据库管理的实际恢复模式为 `SIMPLE`。

在 `SIMPLE` 恢复模式下，数据库日志会自动截断。 在 `FULL` 恢复模式下，日志仅在备份后被截断。 当 SQLLocalDB 在日志文件被截断后重新启动时，它会检测早于最早日志文件的备份 LSN。 因此，它不会启动服务。

查看下一部分中的指南，了解如何执行以下任务：

- 正确确定由于数据库损坏而Microsoft Entra Connect 服务（ADSync）是否未启动 `Model` 。
- 通过从损坏状态恢复 `Model` 数据库来缓解此问题。
- 应用永久修复，确保不会再次发生此 `Model` 数据库损坏。

## 现象

可以验证问题是否基于 Microsoft Entra Connect 服务器中的以下事件：

- 事件查看器：应用程序、EventID 528、源：SQLLocalDB 15.0

  ```
  WaitForMultipleObjects
  575
  {Application Error}
  The application was unable to start correctly (0x%lx). Click OK to close the application.
  3714
  ```
- 事件查看器：Application、EventIDs 2005 和 6226，Source： ADSync

  ```
  0x8023044a
  OriginalError=0x80004005 OLEDB Provider error(s):
  Description  = 'Login timeout expired'
  Failure Code = 0x80004005
  ```
- ADSync 服务配置文件路径\AppData\Local\Microsoft\Microsoft SQL Server Local DB\Instances\ADSync2019 中的 *<SQLLocalDB > error.log文件*

  ```
  <yyyy-MM-dd HH:mm:ss.##> spid14s     The resource database build version is 15.00.4138. This is an informational message only. No user action is required.
  <yyyy-MM-dd HH:mm:ss.##> spid8s      Starting up database 'msdb'.
  <yyyy-MM-dd HH:mm:ss.##> spid14s     Starting up database 'model'.
  <yyyy-MM-dd HH:mm:ss.##> spid14s     Error: 9003, Severity: 20, State: 1.
  <yyyy-MM-dd HH:mm:ss.##> spid14s     The log scan number (41:488:1) passed to log scan in database 'model' is not valid. This error may indicate data corruption or that the log file (.ldf) does not match the data file (.mdf). If this error occurred during replication, re-create the publication. Otherwise, restore from backup if the problem results in a failure during startup.
  <yyyy-MM-dd HH:mm:ss.##> spid14s     SQL Trace was stopped due to server shutdown. Trace ID = '1'. This is an informational message only; no user action is required.
  ```

## 缓解措施

重要

仅当出现所有这些情况时，才应用此处所述的缓解步骤：

- Microsoft Entra Connect 的版本为 2.0。*x.x*.
- Microsoft Entra Connect 随 SQL LocalDB 一起安装。
- [症状*中列出的*所有](#symptoms)条件都存在。

若要从损坏状态恢复 `Model` 数据库，请执行以下步骤：

1. 根据正在运行的服务帐户（例如域帐户、虚拟服务帐户或托管服务帐户）转到以下 ADSync 服务配置文件位置之一：

   - *C：\Users\<service account>\*
   - *C：\Users\ADSyncMSAxxxx$\*
   - *C：\Windows\ServiceProfiles\ADSync\*
2. 在 *以下目录路径中从 ADSync2019 实例文件夹中打开error.log* 文件：

   *<service profile path>\AppData\Local\Microsoft\Microsoft SQL Server Local DB\Instances\ADSync2019\*
3. 在日志中查找以下错误条目，验证 `Model` 数据库是否已损坏：

   ```
   <yyyy-MM-dd HH:mm:ss.##> spid14s     Error: 9003, Severity: 20, State: 1.
   <yyyy-MM-dd HH:mm:ss.##> spid14s     The log scan number (41:488:1) passed to log scan in database 'model' is not valid. This error may indicate data corruption or that the log file (.ldf) does not match the data file (.mdf). If this error occurred during replication, re-create the publication. Otherwise, restore from backup if the problem results in a failure during startup.
   ```
4. 如果此条目中存在错误“9003”，请将此文件夹中的 model.mdf *和 modellog.ldf *文件分别重命名*为old\_model.mdf 和 *old\_modellog.ldf**。
5. 在 *C：\Program Files\Microsoft SQL Server\150\LocalDB\Binn\Templates *处打开 SQL Templates* 文件夹*。
6. 将 *model.mdf* 和 *modellog.ldf* 文件从步骤 2 复制到 ADSync2019 实例文件夹。
7. 启动 ADSync 服务。

## 解决方案

Microsoft已在 Microsoft Entra Connect 版本 2.1.1.0 中引入了此问题的修补程序。 如果同步服务（ADSync）无法启动，则需要应用“缓解”[部分中的步骤](#mitigation)，然后才能升级Microsoft Entra Connect。

若要防止 SQLLocalDB `Model` 数据库中的损坏问题，请安装最新的 Microsoft Entra Connect 内部版本，该版本在 Microsoft Entra Connect：版本发布历史记录[中](/zh-cn/azure/active-directory/hybrid/reference-connect-version-history)可用。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/resolve-model-database-corruption-sqllocaldb)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
