# Windows 冻结的高级故障排除

本文介绍如何排查基于 Windows 的计算机和服务器上的冻结问题。 它还提供收集数据的方法，可帮助管理员或软件开发人员诊断、识别和修复这些问题。

注意

本文中提到的第三方产品由 Microsoft 以外的其他公司提供。 Microsoft 不对这些产品的性能或可靠性提供任何明示或暗示性担保。

*适用于：*Windows 10

## 识别问题

- 哪个计算机正在冻结？ 例如，受影响的计算机是物理服务器或虚拟服务器。
- 冻结时会发生什么操作？ 例如，关闭时会出现此问题。
- 错误发生的频率是多少？ 例如，此问题在晚上 7 点发生。
- 此冻结发生在多少台计算机上？ 例如，所有计算机或只有一台计算机。

## 排查冻结问题

若要排查冻结问题，请检查计算机的当前状态，并遵循以下方法之一。

### 对于仍在处于冻结状态的计算机

如果物理计算机或虚拟机仍然冻结，请使用以下一个或多个方法进行故障排除：

- 尝试通过远程桌面连接访问计算机。
- 使用域帐户或本地管理员帐户通过硬件制造商的远程访问解决方案登录到计算机。 例如，Dell 远程访问卡（DRAC）、HP 集成灯出（iLo）或 IBM 远程监督器适配器（RSA）。
- 测试对计算机的 ping。 查找丢弃的数据包和高网络延迟。
- 访问管理共享，例如 *\\ServerName\c$*。
- 按 Ctrl+Alt+Delete 并检查响应。
- 尝试使用 Windows 远程管理工具。 例如，计算机管理、服务器管理器和 Wmimgmt.msc。

### 对于不再冻结的计算机

如果物理计算机或虚拟机冻结，但现在处于良好状态，请使用以下一个或多个方法进行故障排除。

#### 对于物理计算机

- 查看存在问题的计算机的系统和应用程序日志。 检查相关事件 ID 的事件日志：

  - 应用程序事件日志：应用程序错误，它建议崩溃或相关的系统进程
  - 系统事件日志、关键系统服务的服务控制管理器错误事件 ID
  - 源 Srv/Server 的错误事件 ID 2019/2020
- 通过运行 `perfmon /report`来生成系统诊断报告。

#### 对于虚拟机

- 查看存在问题的计算机的系统和应用程序日志。
- 通过运行 `perfmon /report`来生成系统诊断报告。
- 在虚拟管理监视工具中检查系统的历史记录。

## 收集冻结问题的数据

若要为服务器冻结收集数据，请检查下表，并使用一个或多个建议的方法。

| 计算机类型和状态 | 数据收集方法 |
| --- | --- |
| 处于冻结状态运行的物理计算机 | [使用内存转储文件收集数据](#use-memory-dump-to-collect-data-for-the-physical-computer-thats-running-in-a-frozen-state)。 或使用方法 2、3 或 4。 本部分后面列出了这些方法。 |
| 不再冻结的物理计算机 | 使用方法 1、2、3 或 4。 本部分后面列出了这些方法。 并使用 [池监视器收集数据](#use-pool-monitor-to-collect-data-for-the-physical-computer-that-is-no-longer-frozen)。 |
| 处于冻结状态运行的虚拟机 | Hyper-V 或 VMware： [使用内存转储文件为处于冻结状态](#use-memory-dump-to-collect-data-for-the-virtual-machine-thats-running-in-a-frozen-state)的虚拟机收集数据。   XenServer：使用方法 1、2、3 或 4。 本部分后面列出了这些方法。 |
| 不再冻结的虚拟机 | 使用方法 1、2、3 或 4。 本部分后面列出了这些方法。 |

### 方法 1：内存转储

重要

请认真遵循本部分所述的步骤。 如果注册表修改不正确，可能会发生严重问题。 在修改注册表之前，请[备份注册表](https://support.microsoft.com/topic/how-to-back-up-and-restore-the-registry-in-windows-855140ad-e318-2a13-2829-d428a2ab0692)，以便在出现问题时可以还原。

当计算机意外停止时，完整的内存转储文件将记录系统内存的所有内容。 完整的内存转储文件可能包含收集内存转储文件时正在运行的进程中的数据。

如果计算机不再冻结并且现在处于良好状态，请使用以下步骤启用内存转储，以便在再次发生冻结问题时收集内存转储。 如果虚拟机仍在处于冻结状态，请使用以下步骤启用和收集内存转储。

注意

如果计算机上启用了重启功能，例如 Compaq 计算机中的自动系统重启（ASR）功能，请禁用该功能。 此设置通常在 BIOS 中找到。 启用此功能后，如果 BIOS 未检测到来自操作系统的检测信号，它将重新启动计算机。 重启可能会中断转储进程。

1. 确保计算机设置为获取完整的内存转储文件。

   1. 转到 **“运行** ”并输入 *Sysdm.cpl*，然后按 Enter。
   2. 在**“系统属性**”的**“高级**”选项卡上，选择“**性能>****设置高级”。**> 选择“更改”以检查或更改虚拟内存。
   3. 返回到**启动和恢复**中的**系统属性**>**高级>****设置。**
   4. 在 **“写入调试信息** ”部分中，选择“ **完成内存转储**”。
   5. 选择“ **覆盖任何现有文件**”。
   6. 请确保系统驱动器上有一个分页文件（*pagefile.sys*），并且它至少超过已安装的 RAM（初始大小和最大大小）100 MB。
   7. 确保系统驱动器上的可用空间比物理 RAM 更多。
2. 若要允许系统使用键盘生成转储文件，请启用 `CrashOnCtrlScroll` 注册表值。

   1. 打开注册表编辑器，然后找到以下注册表项：

      - `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\i8042prt\Parameters`
      - `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\kbdhid\Parameters`
   2. 在两个注册表项中创建以下 `CrashOnCtrlScroll` 注册表项：

      - 值名称：`CrashOnCtrlScroll`
      - 数据类型： **REG\_DWORD**
      - 值：**1**
   3. 关闭注册表编辑器并重新启动计算机。
3. 在某些运行早期版本的 Windows 的物理计算机上，可以从 WEB 界面功能（如 DRAC、iLo 或 RSA）生成不可创建的中断（NMI）。 但是，默认情况下，此设置将停止系统，而无需创建内存转储。

   注意

   对于当前支持的 Windows 版本， `NMICrashDump` 不再需要注册表项。 NMI 会导致内存转储数据收集[后出现](nmi-hardware-failure-error)“停止”错误。
4. 当计算机显示问题时，按住右 Ctrl 键，然后按两次滚动锁键生成内存转储文件。

   注意

   默认情况下，转储文件位于以下路径： *%SystemRoot%\MEMORY。DMP*。

### 方法 2：数据健全性检查

使用转储检查实用工具（*Dumpchk.exe*）读取内存转储文件。 它还可以验证文件是否已正确创建且未损坏或无效。

- [使用 DumpChk](/zh-cn/windows-hardware/drivers/debugger/dumpchk)
- [下载 DumpChk](https://developer.microsoft.com/windows/downloads/windows-sdk)

了解如何使用 *Dumpchk.exe* 检查转储文件：

### 方法 3：性能监视器

可以使用 Windows 性能监视器来检查运行的程序如何实时影响计算机的性能，以及收集日志数据以供以后分析。 若要在本地和远程系统上创建性能计数器和事件跟踪日志集合，请在命令提示符下以管理员身份运行以下命令：

```
Logman create counter LOGNAME_Long -u DOMAIN\USERNAME * -f bincirc -v mmddhhmm -max 500 -c "\\COMPUTERNAME\LogicalDisk(*)\*" "\\COMPUTERNAME\Memory\*" "\\COMPUTERNAME\Network Interface(*)\*" "\\COMPUTERNAME\Paging File(*)\*" "\\COMPUTERNAME\PhysicalDisk(*)\*" "\\COMPUTERNAME\Process(*)\*" "\\COMPUTERNAME\Redirector\*" "\\COMPUTERNAME\Server\*" "\\COMPUTERNAME\System\*" "\\COMPUTERNAME\Terminal Services\*" "\\COMPUTERNAME\Processor(*)\*" "\\COMPUTERNAME\Cache\*" -si 00:05:00
```

```
Logman create counter LOGNAME_Short -u DOMAIN\USERNAME * -f bincirc -v mmddhhmm -max 500 -c "\\COMPUTERNAME\LogicalDisk(*)\*" "\\COMPUTERNAME\Memory\*" "\\COMPUTERNAME\Network Interface(*)\*" "\\COMPUTERNAME\Paging File(*)\*" "\\COMPUTERNAME\PhysicalDisk(*)\*" "\\COMPUTERNAME\Process(*)\*" "\\COMPUTERNAME\Redirector\*" "\\COMPUTERNAME\Server\*" "\\COMPUTERNAME\System\*" "\\COMPUTERNAME\Terminal Services\*" "\\COMPUTERNAME\Processor(*)\*" "\\COMPUTERNAME\Cache\*" -si 00:00:10
```

然后，可以通过运行以下命令启动或停止日志：

```
logman start LOGNAME_Long / LOGNAME_Short
logman stop LOGNAME_Long / LOGNAME_Short
```

性能监视器日志位于路径：*C：\PERFLOGS* 中。

### 用于收集数据的其他方法

#### 使用内存转储为处于冻结状态的物理计算机收集数据

警告

请认真遵循本部分所述的步骤。 如果注册表修改不正确，可能会发生严重问题。 在修改注册表之前，请[备份注册表](https://support.microsoft.com/topic/how-to-back-up-and-restore-the-registry-in-windows-855140ad-e318-2a13-2829-d428a2ab0692)，以便在出现问题时可以还原。

如果物理计算机仍在处于冻结状态，请按照以下步骤启用和收集内存转储：

1. 确保计算机已设置为获取完整的内存转储文件，并且可以通过网络访问它。

   注意

   如果无法通过网络访问受影响的计算机，请尝试通过 NMI 生成内存转储文件。 如果以下某些设置未限定，则操作的结果可能不会收集内存转储文件。

   1. 尝试以任何方式访问计算机的桌面。

      注意

      如果无法访问 OS，请尝试在计算机上远程访问注册表编辑器。 然后，可以检查计算机当前配置的内存转储文件和页面文件的类型。
   2. 从最好位于同一网络和子网中的远程计算机中，转到**注册表编辑器>连接网络注册表。** 然后，连接到受影响的计算机，并验证以下设置：

      - `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\CrashControl\CrashDumpEnabled`

        确保 [CrashDumpEnabled](/zh-cn/previous-versions/windows/it-pro/windows-2000-server/cc976050(v=technet.10)) 注册表项为 **1**。
      - `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\CrashControl\NMICrashDump`

        在某些物理服务器上，如果 `NMICrashDump` 注册表项存在并且其值为 **1**，则可以从远程管理提供程序（如 DRAC、iLo 和 RSA）利用 NMI。
      - `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PagingFiles and ExistingPageFiles`

        如果注册表项的值 `Pagefile` 是系统管理的，则大小不会反映在注册表中。 例如： `?:\pagefile.sys)`

        如果自定义页面文件，则大小将反映在注册表中，例如 `?:\pagefile.sys 1024 1124`。 在此示例中，1024 是初始大小，1124 是最大大小。

        注意

        如果注册表中未反映大小，请尝试访问页面文件所在的管理共享。 例如 *\\ServerName\C$*。
   3. 请确保计算机上的系统驱动器上有一个分页文件（pagefile.sys），并且它至少超过已安装的 RAM 100 MB。
   4. 确保计算机的硬盘驱动器上具有比物理 RAM 更多的可用空间。
2. **在计算机上启用 CrashOnCtrlScroll** 注册表值，以允许系统使用键盘生成转储文件。

   1. 从远程计算机最好位于同一网络和子网中，转到**注册表编辑器>连接网络注册表。** 连接到受影响的计算机并找到以下注册表项：

      - `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\i8042prt\Parameters`
      - `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\kbdhid\Parameters`
   2. 在两个注册表项中创建以下 `CrashOnCtrlScroll` 注册表项：

      值名称：数据类型： `CrashOnCtrlScroll` **REG\_DWORD** 值： **1**
   3. 关闭注册表编辑器并重新启动计算机。
3. 当计算机显示问题时，按住右 Ctrl 键，然后按两次滚动锁键生成内存转储。

   注意

   默认情况下，转储文件位于路径 ： *%SystemRoot%\MEMORY 中。DMP*。

### 使用池监视器为不再冻结的物理计算机收集数据

池监视器显示按池类型分配的分配数和未完成的字节数，以及传递给 ExAllocatePoolWithTag 调用的标记。

有关详细信息，请参阅 [使用 PoolMon 查找内核模式内存泄漏](/zh-cn/windows-hardware/drivers/debugger/using-poolmon-to-find-a-kernel-mode-memory-leak) 和 [PoolMon 示例](/zh-cn/windows-hardware/drivers/devtest/poolmon-examples)。

### 使用内存转储为处于冻结状态的虚拟机收集数据

对运行虚拟机的应用程序使用以下方法之一。

#### Microsoft Hyper-V

还可以通过 [Debug-VM](/zh-cn/powershell/module/hyper-v/debug-vm) cmdlet 使用内置的 NMI 功能来调试和获取内存转储。

若要调试 Hyper-V 上的虚拟机，请在 Windows PowerShell 中运行以下 cmdlet：

```
Debug-VM -Name "VM Name" -InjectNonMaskableInterrupt -ComputerName Hostname
```

#### VMware

可以使用 VMware 快照或挂起状态，并提取与完整内存转储文件等效的内存转储文件。 使用 VMware 的 [检查点到核心工具（vmss2core）](https://kb.vmware.com/s/article/2003941) 将挂起（`.vmss`）和快照（`.vmsn`）状态文件转换为转储文件。 然后使用标准 Windows 调试工具分析文件。

注意

使用 Microsoft 支持部门时，应使用 VMware 的[检查点到核心工具（vmss2core）](https://kb.vmware.com/s/article/2003941)将 VMware 快照转换为转储文件，然后再将其上传到Microsoft。 如果快照转换遇到任何问题，请联系 VMware 以获取支持。

#### Citrix XenServer

内存转储过程通过按向右 Ctrl+Scroll Lock+Scroll Lock 键盘组合进行。 有关详细信息，请参阅如何从 Citrix 的 XenServer [上运行的 Windows 虚拟机触发内存转储的方法 1](https://support.citrix.com/article/ctx123177)。

## Windows Server 中系统驱动器的空间限制

在 Windows Server 上，可能没有足够的可用磁盘空间来在系统卷上生成完整的内存转储文件。

如果系统驱动器没有足够的空间，则有第二个选项。 可以使用 `DedicatedDumpFile` 注册表项。 有关详细信息，请参阅 [配置内存转储](/zh-cn/windows-server/administration/server-core/server-core-memory-dump#step-2-configure-the-destination-path-for-a-memory-dump)的目标路径。

有关详细信息，请参阅 [如何使用 DedicatedDumpFile 注册表值来克服系统驱动器](/zh-cn/archive/blogs/ntdebugging/how-to-use-the-dedicateddumpfile-registry-value-to-overcome-space-limitations-on-the-system-drive-when-capturing-a-system-memory-dump)的空间限制。

**第三方联系人免责声明**

Microsoft 会提供第三方联系信息来帮助你查找有关本主题的其他信息。 此联系信息可能会更改，恕不另行通知。 Microsoft 不保证第三方联系信息的准确性。

**第三方信息免责声明**

本文中提到的第三方产品由 Microsoft 以外的其他公司提供。 Microsoft 不对这些产品的性能或可靠性提供任何明示或暗示性担保。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/windows-based-computer-freeze-troubleshooting)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
