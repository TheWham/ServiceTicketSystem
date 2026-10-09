# 安装包含发布问题的 10 月 10 日版本的KB4041676或KB4041691后，Windows 设备可能无法启动

本文提供了 Windows 设备在安装 10 月 10 日版本KB4041676或KB4041691后可能无法启动的问题的解决方法。

*适用于：* Windows Server 2016、Windows 10 版本 1607、Windows 10 版本 1703  
*原始 KB 数：* 4049094

## 概述

Microsoft知道适用于 WSUS/SCCM 托管设备的 Windows 10 版本 1703（KB4041676）和版本 1607（KB4041691）和 Windows Server 2016（KB4041691）2017 年 10 月 10 日每月安全更新的发布问题。 直接从 Windows 更新（家庭和使用者设备）或适用于企业的Windows 更新下载更新的客户不会受到影响。

截至 10 月 10 日下午，我们更正了发布问题，并验证了累积安全更新。 我们建议所有客户采用这些累积安全更新。

我们报告了以下影响 Windows Server Update Services （WSUS） 和 System Center Configuration Manager （SCCM） 客户的症状。 可在下面找到以下用户报告方案的缓解计划。

1. 在 10 月 10 日下午 4 点之前同步了 10 月 10 日更新（KB4041676或KB4041691）的 WSUS/SCCM 管理员可能仍缓存这些 KB。
2. 下载 10 月 10 日KB4041676或KB4041691发布问题的 WSUS/SCCM 托管设备，并让设备处于挂起的重新启动状态。
3. 安装了 10 月 10 日KB4041676或KB4041691更新的 WSUS/SCCM 托管设备，并且无法启动和/或可能登陆恢复屏幕。

## 问题详细信息

### 方案 1

在 10 月 10 日下午 4 点之前同步 KB4041676 或 KB4041691 Delta 包版本的 WSUS/SCCM 管理员可能仍缓存这些 KB。

#### 解决方法

WSUS/SCCM 管理员应重新扫描更新以自动解决发布问题。 此问题已在 10 月 10 日下午 4 点以来扫描的 WSUS 层次结构中得到解决。 确保上游和下游服务器同步。

### 方案 2

已下载并暂存 KB4041676 或 KB4041691 的 Delta 包版本的 WSUS/SCCM 托管设备，但尚未重新启动以安装。

#### 解决方法

如果设备已下载并暂存了 KB4041676 或 KB4041691 的 Delta 包版本，则重启后，用户可能无法启动。 系统管理员可以通过从设备上的管理命令提示符运行以下命令来删除挂起的更新：

```
@echo off

REM Stop all update related services
net stop usosvc
net stop wuauserv
net stop trustedinstaller

REM Delete pending.xml if it exists
takeown /f %windir%\winsxs\pending.xml >NUL 2>&1
icacls %windir%\winsxs\pending.xml /grant Everyone:F >NUL 2>&1
del %windir%\winsxs\pending.xml >NUL 2>&1

REM Modify the components hive
reg unload HKLM\Components >NUL 2>&1
reg load HKLM\ComponentsHive %windir%\system32\config\COMPONENTS
reg delete /f HKLM\ComponentsHive /v PendingXmlIdentifier >NUL 2>&1
reg delete /f HKLM\ComponentsHive /v PoqexecFailure >NUL 2>&1
reg delete /f HKLM\ComponentsHive /v ExecutionState >NUL 2>&1
reg delete /f HKLM\ComponentsHive /v RepairTransactionPended >NUL 2>&1
reg delete /f HKLM\ComponentsHive /v AIFailureInformation >NUL 2>&1
reg delete /f HKLM\ComponentsHive\Installers\RegKeySDTable /v Install >NUL 2>&1
reg delete /f HKLM\ComponentsHive\Installers\RegKeySDTable /v Uninstall >NUL 2>&1
reg delete /f HKLM\ComponentsHive\Installers\RegKeySDTable /v Uninstall >NUL 2>&1
reg unload HKLM\ComponentsHive

REM Stop Poqexec from running
reg delete /f HKLM\Software\Microsoft\Windows\CurrentVersion\SideBySide\Configuration /v DontRunPoqexecInSmss >NUL 2>&1
reg delete /f HKLM\Software\Microsoft\Windows\CurrentVersion\SideBySide\Configuration /v PoqexecCmdline >NUL 2>&1
reg delete /f "HKLM\System\CurrentControlSet\Control\Session Manager" /v SETUPEXECUTE >NUL 2>&1
REG ADD "HKLM\System\CurrentControlSet\Control\Session Manager" /v SETUPEXECUTE /t REG_MULTI_SZ /d \0 /f

dism /online /remove-package /PackageName:Package_for_RollupFix_Wrapper~31bf3856ad364e35~amd64~~15063.674.1.8 /norestart >NUL 2>&1
dism /online /remove-package /PackageName:Package_for_RollupFix_Wrapper~31bf3856ad364e35~x86~~15063.674.1.8 /norestart >NUL 2>&1
dism /online /remove-package /PackageName:Package_for_RollupFix_Wrapper~31bf3856ad364e35~amd64~~14393.1770.1.6 /norestart >NUL 2>&1
dism /online /remove-package /PackageName:Package_for_RollupFix_Wrapper~31bf3856ad364e35~x86~~14393.1770.1.6 /norestart >NUL 2>&1
```

### 方案 3

安装了 delta Package 版本的 KB4041676 或 KB4041691 且无法启动和/或看到恢复屏幕的 WSUS/SCCM 托管设备

#### 解决方法

重要

只有在无法启动的设备上才应遵循这些步骤。

1. 插入 AC 电源并打开设备。
2. 如果设备无法启动，Windows 将尝试修复设备并输入 Windows 10 恢复环境。 在“自动修复”屏幕上选择**“高级”选项****。**

   ![自动修复屏幕的屏幕截图。](media/windows-devices-fail-boot-after-installing-kb4041676-kb4041691/automatic-repair.png)
3. 依次选择“故障排除”、“**高级选项”**和**“系统还原**”。**** 如果在安装KB4041676或KB4041691之前提供了还原点，请使用 **系统还原** 向导还原到以前的还原点。 如果还原点不存在，请关闭 **系统还原** 并继续执行下一步。
4. 依次选择“故障排除”、“**高级选项”**和**“命令提示符**”。**** 系统可能会要求输入 BitLocker 恢复密钥或用户名/密码。 如果系统提示输入用户名/密码，则必须输入本地帐户。 如果没有凭据，则许多人需要创建和使用 [恢复驱动器](https://support.microsoft.com/help/4026852/windows-create-a-recovery-drive)。

   ![“高级选项”屏幕的屏幕截图。](media/windows-devices-fail-boot-after-installing-kb4041676-kb4041691/advanced-options.png)
5. **命令提示符**启动后，运行以下命令以加载软件注册表配置单元：

   ```
   reg load hklm\temp <drive letter for windows directory>\windows\system32\config\software
   ```

   **示例：**

   ```
   reg load hklm\temp c:\windows\system32\config\software
   ```
6. 运行以下命令以删除 SessionsPending 注册表项。 如果注册表值不存在，请继续执行下一步。

   ```
   reg delete "HKLM\temp\Microsoft\Windows\CurrentVersion\Component Based Servicing\SessionsPending" /v Exclusive
   ```
7. 运行以下命令以卸载注册表：

   ```
   reg unload HKLM\temp
   ```
8. 运行以下命令，这将列出所有挂起的更新：

   ```
   dism.exe /image:<drive letter for windows directory> /Get-Packages
   ```

   **示例：**

   ```
   dism.exe /image:c:\ /Get-Packages
   ```
9. 针对状态 = 安装挂起的每个包运行以下命令：

   ```
   dism.exe /image:<drive letter for windows directory> /remove-package /packagename:<package name>
   ```

   **示例：**

   ```
   dism.exe /image:c:\ /remove-package /packagename:Package_for_RollupFix_Wrapper~31bf3856ad365e35~amd64~~15063.674.1.8
   ```

   ```
   dism.exe /image:c:\ /remove-package /packagename:Package_for_RollupFix~31bf3856ad365e35~amd64~~15063.674.1.8
   ```
10. **关闭命令提示符**，然后单击“继续”退出恢复环境。

    ![“选择选项”屏幕的屏幕截图。](media/windows-devices-fail-boot-after-installing-kb4041676-kb4041691/continue-dialog.png)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/windows-devices-fail-boot-after-installing-kb4041676-kb4041691)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
