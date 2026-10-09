# 排查 Microsoft Entra Connect 升级问题

## 概要

本文介绍如何排查从以前安装的 Microsoft Entra Connect、Azure AD Sync 或 DirSync 升级到最新版本的 Microsoft Entra Connect 时可能出现的问题。

警告

你可能会找到一些联机文档，其中包括直接编辑 Windows 注册表的步骤。 但是，如果修改注册表不正确，编辑注册表可能会导致严重问题。 Microsoft Entra Connect 产品团队 **不支持** 编辑 Windows 注册表。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 4051210

## 现象

每次启动 Microsoft Entra Connect 安装向导时，程序都会评估当前安装的所有相关产品和 Windows Installer 包（.msi）。 若要跟踪此活动，请执行以下步骤：

1. 启动Microsoft Entra Connect 向导，并等待第一页打开。
2. `%ProgramData%\AADConnect\`打开文件夹并分析最新的安装跟踪日志。
3. 找到其中 `GetInstalledPackagesByUpgradeCode`向导评估 Windows 中安装的所有相关 Windows Installer 包的条目。 例如：

   ```
   [10:44:23.095] [ 1] [INFO ] Performing direct lookup of upgrade codes for: Azure AD Sync Engine
   [10:44:23.095] [ 1] [VERB ] Getting list of installed packages by upgrade code
   [10:44:23.095] [ 1] [INFO ] GetInstalledPackagesByUpgradeCode {545334d7-13cd-4bab-8da1-2775fa8cf7c2}: verified product code {7c4397b7-9008-4c23-8cda-3b3b8faf4312}.
   [10:44:23.095] [ 1] [INFO ] GetInstalledPackagesByUpgradeCode {dc9e604e-37b0-4efc-b429-21721cf49d0d}: no registered products found.
   [10:44:23.095] [ 1] [INFO ] GetInstalledPackagesByUpgradeCode {bef7e7d9-2ac2-44b9-abfc-3335222b92a7}: no registered products found.
   ```

可以在跟踪日志的此部分附近找到两种类似的症状：

产品已卸载，但 Windows 中仍然存在不一致的错误代码。向导正在检测同步引擎的旧安装：“已安装产品 Azure AD 同步引擎（版本 1.1.343.0），需要升级到版本 1.1.380.0。

```
[10:44:23.095] [ 1] [VERB ] Package=Microsoft Azure AD Connect synchronization services, Version=1.1.343.0, ProductCode=7c4397b7-9008-4c23-8cda-3b3b8faf4312, UpgradeCode=545334d7-13cd-4bab-8da1-2775fa8cf7c2
[10:44:23.095] [ 1] [INFO ] Determining installation action for Azure AD Sync Engine (545334d7-13cd-4bab-8da1-2775fa8cf7c2)
[10:44:23.298] [ 1] [VERB ] Check product code installed: {4e67cad2-d71b-4f06-a7ae-bb49c566bb93}
[10:44:23.298] [ 1] [INFO ] GetProductInfoProperty({4e67cad2-d71b-4f06-a7ae-bb49c566bb93}, VersionString): unknown product
[10:44:23.298] [ 1] [INFO ] AzureADSyncEngineComponent: Product Azure AD Sync Engine (version 1.1.343.0) is installed, needs to be upgraded to version 1.1.380.0.
```

但是，卸载此产品后，Windows Installer 信息可能不一致，并且同步引擎不再存在。

由于安装向导仍在检测旧的代码示例，因此它决定升级 Azure AD 同步引擎，而不是执行干净安装。 在升级过程中，当安装程序正在检查当前服务状态时，安装会失败，因为 ADSync 服务不存在：

```
[10:44:28.260] [ 1] [INFO ] ServiceControllerProvider: verifying ADSync is in state (Running)
[10:44:28.291] [ 1] [ERROR] Caught an exception while creating the initial page set on the root page.
Exception Data (Raw): System.InvalidOperationException: Service ADSync was not found on computer '.'. ---> System.ComponentModel.Win32Exception: The specified service does not exist as an installed service
```

产品已卸载，但 Windows 中仍存在过时的错误代码

在 Windows Installer 程序包中找到的过时的代码示例也可能导致升级问题。

```
[15:29:06.958] [ 1] [INFO ] Performing direct lookup of upgrade codes for: Azure AD Sync Engine
[15:29:06.959] [ 1] [VERB ] Getting list of installed packages by upgrade code
[15:29:06.959] [ 1] [INFO ] GetProductInfoProperty({7c4397b7-9008-4c23-8cda-3b3b8faf4312}, VersionString): unrecognized error (1608)
[15:29:06.959] [ 1] [INFO ] GetInstalledPackagesByUpgradeCode {545334d7-13cd-4bab-8da1-2775fa8cf7c2}: stale product code {7c4397b7-9008-4c23-8cda-3b3b8faf4312}.
[15:29:06.959] [ 1] [INFO ] GetInstalledPackagesByUpgradeCode {545334d7-13cd-4bab-8da1-2775fa8cf7c2}: no registered products found.
[15:29:06.959] [ 1] [INFO ] GetInstalledPackagesByUpgradeCode {dc9e604e-37b0-4efc-b429-21721cf49d0d}: no registered products found.
[15:29:06.959] [ 1] [INFO ] GetInstalledPackagesByUpgradeCode {bef7e7d9-2ac2-44b9-abfc-3335222b92a7}: no registered products found.
[15:29:06.963] [ 1] [INFO ] Determining installation action for Azure AD Sync Engine (545334d7-13cd-4bab-8da1-2775fa8cf7c2)
[15:29:07.059] [ 1] [INFO ] Product Azure AD Sync Engine is not installed.
```

Microsoft Entra Connect 安装向导无法检测到已安装 Azure AD 同步引擎。 安装程序失败并返回以下错误消息：

```
[15:52:17.674] [ 13] [ERROR] PerformConfigurationPageViewModel: Caught exception while installing synchronization service.
Exception Data (Raw): System.Exception: Unable to install the Synchronization Service. Please see the event log for additional details. ---> Microsoft.Azure.ActiveDirectory.Client.Framework.ProcessExecutionFailedException: Error installing msi package 'Synchronization Service.msi'. Full log is available at 'C:\ProgramData\AADConnect\Synchronization Service_Install-20170525-155217.log'.
...
MSI (s) (C0!08) [15:52:17:605]: Product: Microsoft Azure AD Connect synchronization services -- Error 25019.The Microsoft Azure AD Connect synchronization services setup wizard cannot open registry key SYSTEM\CurrentControlSet\Services\ADSync\Parameters. Try verifying the key and running this wizard again. The system cannot find the file specified.
CustomAction DetectStoreServer returned actual error code 1603 (note this may not be 100% accurate if translation happened inside sandbox)
Action ended 15:52:17: DetectStoreServer.
---> Microsoft.Azure.ActiveDirectory.Client.Framework.ProcessExecutionFailedException: Exception: Execution failed with errorCode: 1603.
```

发生此错误的原因是 MSIEXEC 进程仍尝试升级 Azure AD 同步引擎，如同步Service\_Install-20170525-155217.log*文件中所示*：

```
MSI (s) (C0:0C) [15:52:17:386]: PROPERTY CHANGE: Adding WIX_UPGRADE_DETECTED property. Its value is '{7C4397B7-9008-4C23-8CDA-3B3B8FAF4312}'.
MSI (s) (C0:0C) [15:52:17:386]: PROPERTY CHANGE: Adding MIGRATE property. Its value is '{7C4397B7-9008-4C23-8CDA-3B3B8FAF4312}'.
...
MSI (s) (C0:D4) [15:52:17:598]: Invoking remote custom action. DLL: C:\Windows\Installer\MSI1D9A.tmp, Entrypoint: DetectStoreServer
Action start 15:52:17: DetectStoreServer.
MSI (s) (C0!08) [15:52:17:605]: Product: Microsoft Azure AD Connect synchronization services -- Error 25019.The Microsoft Azure AD Connect synchronization services setup wizard cannot open registry key SYSTEM\CurrentControlSet\Services\ADSync\Parameters. Try verifying the key and running this wizard again. The system cannot find the file specified.
```

与前面的情况一样，Windows Installer 升级过程失败，因为注册表中的 ADSync 服务条目不存在。 之前已卸载该产品，使 Windows Installer 数据库不一致。

## 解决方案

可以为跟踪日志中标识的 Azure AD 同步引擎错误代码清理 Windows Installer 数据库上的不一致。 （产品代码可能有所不同。对于前面的示例，有问题的代码示例为 7c4397b7-9008-4c23-8cda-3b3b8faf4312。

从跟踪日志中识别有问题的代码示例后，请根据需要使用以下方法。

修复 Windows Installer 问题（如果适用）， KB3139923 Windows 修补程序可能会导致这些 Windows Installer 问题。 因此，建议将其卸载。

若要检查是否已安装KB3139923，请转到>> 或使用 PowerShell 导出所有已安装修补程序的列表：

```
Get-Hotfix |
Select-Object HotFixID, InstalledOn, Description, InstalledBy |
Sort-Object –Property InstalledOn –Descending |
Out-File –FilePath ".\$env:COMPUTERNAME-HotFixes.txt"
```

1. 如果存在KB3139923修补程序，请将其卸载，然后重启服务器。
2. 下载并安装 [KB3072630 Windows 修补程序](https://www.microsoft.com/download/details.aspx?id=47955)，然后再次重启。

使用 Windows Installer 命令行工具卸载代码示例

若要卸载 Azure AD 同步引擎的代码示例，请运行 Windows Installer 命令行工具（[MsiExec.exe](/zh-cn/windows-server/administration/windows-commands/msiexec)），如下所示：

1. 从跟踪日志（GUID）中识别不一致或过时的代码示例，如“症状”部分所示。
2. 打开管理员“命令提示符”窗口。
3. 通过验证有问题的错误代码的实际 GUID 来输入以下行：

   ```
   SET productcode={<12345678-0000-abcd-0000-0123456789ab>}
   ```
4. 输入以下命令，重复该命令，然后重启服务器。

   注意

   由于 Windows Installer 数据库已损坏，你可能会看到许多报告的错误。 对于出现的任何对话框，请选择“ **是**”。

   ```
   SET /a counter+=1
   & MSIEXEC /x %productcode% /qn /norestart /l*v "%ProgramData%\AADConnect\AADConnect_Uninstall-ForcedUninstall_%counter%.log" EXECUTE_UNINSTALL="1"
   ```
5. 启动Microsoft Entra Connect 向导，并等待第一页打开。
6. `%ProgramData%\AADConnect\`打开文件夹并分析最新的安装跟踪日志。
7. 如果日志文件中不再存在不一致或过时的代码示例，请继续向导并完成安装。 否则，请转到下一个解决方案。

使用程序安装和卸载疑难解答工具

如果被阻止安装或删除程序，程序安装和卸载疑难解答可帮助你自动修复问题。 它还修复了损坏的注册表项。

[修复阻止安装或删除程序的问题（microsoft.com）](https://support.microsoft.com/en-us/topic/fix-problems-that-block-programs-from-being-installed-or-removed-cca7d1b6-65a9-3d98-426b-e9f927e1eb4d)

运行该工具后，重启服务器，然后执行以下步骤：

1. 启动Microsoft Entra Connect 向导，并等待第一页打开。
2. `%ProgramData%\AADConnect\`打开文件夹并分析最新的安装跟踪日志。
3. 如果日志文件中不再存在不一致或过时的代码示例，请继续向导并完成安装。 如果存在过时的代码示例，建议重新安装 Windows 操作系统，因为你无法从不一致的状态恢复 Windows Installer 数据库。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/troubleshoot-aad-connect-fails-to-install-upgraded-version)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
