# 停止代码错误的高级故障排除

[**试用我们的虚拟代理**](https://vsa.services.microsoft.com/v1.0/?partnerId=7d74cf73-5217-4008-833f-87a1a278f2cb&flowId=DMC&initialQuery=31806236) - 它可以帮助快速识别和修复常见的 Windows 启动问题

注释

如果你不是支持代理或 IT 专业人员，可以在 [“解决停止代码错误”中找到有关停止代码](https://support.microsoft.com/sbs/windows/troubleshoot-blue-screen-errors-5c62726c-6489-52da-a372-3f73142c14ad)错误消息的更多有用信息。

*适用于：*受支持的 Windows Server 和 Windows 客户端版本

## 导致停止错误的原因是什么？

当 Windows 遇到影响安全运行的状况时，系统将停止。 示例包括可能危及安全性或导致作系统（OS）和/或用户数据损坏的故障。 当计算机停止以防止操作系统在这些条件下向前移动时，这称为 bug 检查。 它通常也称为系统崩溃、内核错误或停止代码错误。 在 Windows 预览版上，屏幕颜色可能会变成绿色，这会导致出现“绿色死亡屏幕”（GSOD）。

对于系统崩溃错误的原因，没有简单的方法来解释。 可以涉及许多不同的因素。 我们对崩溃根源的分析表明：

- 70% 是由第三方驱动程序代码引起的。
- 10% 是由硬件问题引起的。
- 5% 是由Microsoft代码引起的。
- 15% 有未知原因，因为内存太损坏，无法分析。

注释

停止错误的根本原因很少是用户模式进程。 虽然用户模式进程（如记事本或 Slack）可能会触发停止错误，但它通常会在驱动程序、硬件或操作系统中揭示底层问题。

## 常规故障排除步骤

若要排查停止错误消息的问题，请遵循以下常规步骤：

1. 查看在事件日志中找到的停止错误代码。 联机搜索特定的停止错误代码，以查看是否存在任何已知问题、解决办法或变通方案。
2. 请确保安装最新的 Windows 更新、累积更新和汇总更新。 若要验证更新状态，请参阅系统的相应更新历史记录。 例如：

   - [Windows 10 版本 21H2](https://support.microsoft.com/topic/windows-10-update-history-857b8ccb-71e4-49e5-b3f6-7073197d98fb)
   - [Windows 10 版本 21H1](https://support.microsoft.com/topic/windows-10-update-history-1b6aac92-bf01-42b5-b158-f80c6d93eb11)
   - [Windows 10 版本 20H2](https://support.microsoft.com/topic/windows-10-update-history-7dd3071a-3906-fa2c-c342-f7f86728a6e3)
3. 请确保 BIOS 和固件是最新版本。
4. 运行任何相关的硬件和内存测试。
5. 运行 [Microsoft安全扫描程序](/zh-cn/microsoft-365/security/intelligence/safety-scanner-download) 或任何其他病毒检测程序，包括检查 MBR 是否存在感染。
6. 确保硬盘上有足够的可用空间。 确切的要求各不相同，但我们建议 10-15% 的可用磁盘空间。
7. 在以下情况下，请与相应的硬件或软件供应商联系来更新驱动程序和应用程序：

   - 错误消息指示特定驱动程序导致了该问题。
   - 你会看到服务在崩溃发生之前启动或停止的迹象。 在这种情况下，确定服务行为是否在所有崩溃实例中保持一致。
   - 你进行了任何软件或硬件更改。

   注释

   如果特定制造商没有可用的更新，建议禁用相关服务。

   有关详细信息，请参阅[如何在 Windows 中执行干净启动](https://support.microsoft.com/topic/how-to-perform-a-clean-boot-in-windows-da2f9573-6eec-00ad-2f8a-a97a1807f3dd)。

   可以按照 [“如何在 Windows 中暂时停用内核模式筛选器驱动程序](../../windows-server/performance/deactivate-kernel-mode-filter-driver)”中的步骤禁用驱动程序。

   还可以考虑回滚更改或还原到最后已知工作状态的选项。 有关详细信息，请参阅 [将设备驱动程序回滚到以前的版本](/zh-cn/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/cc732648(v=ws.11))。

### 内存转储收集

若要为内存转储文件配置系统，请执行以下步骤：

1. 选择任务栏搜索框，键入 *高级系统设置*，然后按 **Enter**。
2. 在**“系统属性**”框的“**高级**”选项卡上，选择“**启动和恢复**”部分中显示的**“设置”**按钮。
3. 在新窗口中，选择选项“ **写入调试信息**”下方的下拉列表。
4. 选择 **“自动内存转储**”。
5. 选择**“确定”**。
6. 重启计算机，使设置生效。
7. 如果服务器已虚拟化，请在创建内存转储文件后禁用自动重新启动。 通过禁用功能，可以创建服务器当前状态的快照，以便在问题再次发生时进行分析。

内存转储文件保存在以下位置：

| 转储文件类型 | 位置 |
| --- | --- |
| (无) | *%SystemRoot%\MEMORY.DMP* （未激活或灰色显示） |
| 小型内存转储文件（256 KB） | *%SystemRoot%\Minidump* |
| 内核内存转储文件 | *%SystemRoot%\MEMORY.DMP* |
| 完整内存转储文件 | *%SystemRoot%\MEMORY.DMP* |
| 自动内存转储文件 | *%SystemRoot%\MEMORY.DMP* |
| 活动内存转储文件 | *%SystemRoot%\MEMORY.DMP* |

可以使用Microsoft故障转储文件检查器（DumpChk）工具来验证内存转储文件是否已损坏或无效。 有关详细信息，请参阅以下视频：

有关如何使用 *Dumpchk.exe* 检查转储文件的详细信息，请参阅以下文章：

- [使用 DumpChk](/zh-cn/windows-hardware/drivers/debugger/dumpchk)
- [下载 DumpChk](https://developer.microsoft.com/windows/downloads/windows-sdk)

### Pagefile 设置

有关页面文件设置的详细信息，请参阅以下文章：

- [页面文件简介](introduction-to-the-page-file)
- [如何确定 64 位版本 Windows 的合适页面文件大小](how-to-determine-the-appropriate-page-file-size-for-64-bit-versions-of-windows)
- [生成内核或完整的故障转储](generate-a-kernel-or-complete-crash-dump)

### 内存转储分析

查找崩溃的根本原因可能并不容易。 硬件问题尤其难以诊断，因为它们可能会导致不稳定和不可预知的行为，这些行为可以表现在各种症状中。

发生停止错误时，应首先隔离有问题的组件，然后尝试导致它们再次触发停止错误。 如果可以复制问题，通常可以确定原因。

可以使用 Windows 软件开发工具包（SDK）和符号等工具来诊断转储日志。 下一部分讨论如何使用此工具。

## 高级故障排除步骤

注释

如果编程和内部 Windows 机制没有经验，则故障转储的高级故障排除可能非常具有挑战性。 我们试图在此处简要了解所使用的一些技术，包括一些示例。 但是，为了真正有效地解决转储故障，您应该花时间去熟悉高级调试技术。 有关视频概述， [调试内核模式崩溃并挂起](/zh-cn/shows/defrag-tools/defragtools-137-debugging-kernel-mode-dumps)。 另请参阅下面列出的高级引用。

### 高级调试参考

- [高级 Windows 调试，第一版书籍](https://www.amazon.com/Advanced-Windows-Debugging-Mario-Hewardt/dp/0321374460)
- [Windows 调试工具（WinDbg、KD、CDB、NTSD）](/zh-cn/windows-hardware/drivers/debugger/)

### 调试步骤

1. 验证计算机是否已设置为在发生崩溃时生成完整的内存转储文件。 有关详细信息，请参阅 [方法 1：内存转储](windows-based-computer-freeze-troubleshooting#method-1-memory-dump)。
2. 在崩溃的计算机上的 Windows 目录中找到 *memory.dmp* 文件，并将该文件复制到另一台计算机。
3. 在其他计算机上，下载 [Windows 10 SDK](https://developer.microsoft.com/windows/downloads/windows-sdk)。
4. 启动安装并选择 **“适用于 Windows 的调试工具**”。 已安装 WinDbg 工具。
5. 转到“ **文件** ”菜单，选择 **“符号文件路径** ”以打开 WinDbg 工具并设置符号路径。

   1. 如果计算机连接到 Internet，请输入 [Microsoft公共符号服务器](/zh-cn/windows-hardware/drivers/debugger/microsoft-public-symbols)： `https://msdl.microsoft.com/download/symbols` 然后选择“ **确定**”。 建议使用此方法。
   2. 如果计算机未连接到 Internet，请指定本地 [符号路径](/zh-cn/windows-hardware/drivers/debugger/symbol-path)。
6. 选择**“打开故障转储”**，然后打开你复制的*memory.dmp* 文件。

   ![打开故障转储文件时 WinDbg 中示例输出的屏幕截图。](media/stop-error-or-blue-screen-error-troubleshooting/windbg-dump-file.png)
7. 在 **错误检查分析** 下，选择 **`!analyze -v`**。 该命令 `!analyze -v` 在页面底部的提示符中输入。
8. 将呈现详细的故障检查分析。

   ![详细故障检测分析示例的屏幕截图。](media/stop-error-or-blue-screen-error-troubleshooting/bugcheck-analysis.png)
9. 向下滚动到 **STACK\_TEXT** 部分。 这些数字会排列成行，每行后面跟着一个冒号和一些文本。 该文本应告知 DLL 导致崩溃的原因。 如果适用，它还显示哪个服务正在崩溃 DLL。
10. 有关如何解释STACK\_TEXT输出的详细信息，请参阅 [使用 ！analyze 扩展](/zh-cn/windows-hardware/drivers/debugger/using-the--analyze-extension)。

存在许多可能导致 bug 检查的原因，每个情况都是唯一的。 在上面提供的示例中，可从 STACK\_TEXT 中识别的重要句行是 20、21 和 22。

注释

此处删除了 HEX 数据，为了清楚起见，行数已编号。

```
1  : nt!KeBugCheckEx
2  : nt!PspCatchCriticalBreak+0xff
3  : nt!PspTerminateAllThreads+0x1134cf
4  : nt!PspTerminateProcess+0xe0
5  : nt!NtTerminateProcess+0xa9
6  : nt!KiSystemServiceCopyEnd+0x13
7  : nt!KiServiceLinkage
8  : nt!KiDispatchException+0x1107fe
9  : nt!KiFastFailDispatch+0xe4
10 : nt!KiRaiseSecurityCheckFailure+0x3d3
11 : ntdll!RtlpHpFreeWithExceptionProtection$filt$0+0x44
12 : ntdll!_C_specific_handler+0x96
13 : ntdll!RtlpExecuteHandlerForException+0xd
14 : ntdll!RtlDispatchException+0x358
15 : ntdll!KiUserExceptionDispatch+0x2e
16 : ntdll!RtlpHpVsContextFree+0x11e
17 : ntdll!RtlpHpFreeHeap+0x48c
18 : ntdll!RtlpHpFreeWithExceptionProtection+0xda
19 : ntdll!RtlFreeHeap+0x24a
20 : FWPolicyIOMgr!FwBinariesFree+0xa7c2
21 : mpssvc!FwMoneisDiagEdpPolicyUpdate+0x1584f
22 : mpssvc!FwEdpMonUpdate+0x6c
23 : ntdll!RtlpWnfWalkUserSubscriptionList+0x29b
24 : ntdll!RtlpWnfProcessCurrentDescriptor+0x105
25 : ntdll!RtlpWnfNotificationThread+0x80
26 : ntdll!TppExecuteWaitCallback+0xe1
27 : ntdll!TppWorkerThread+0x8d0
28 : KERNEL32!BaseThreadInitThunk+0x14
29 : ntdll!RtlUserThreadStart+0x21
```

此问题是因为 mpssvc 服务是 Windows 防火墙的一个组件。 此问题是通过暂时禁用防火墙，然后重置防火墙策略来修复的。

有关更多示例，请参阅 [调试示例](#debugging-examples)。

## 视频资源

以下视频演示了用于分析转储文件的各种故障排除技术。

- [分析转储文件](https://www.youtube.com/watch?v=s5Vwnmi_TEY)
- [安装适用于 Windows 的调试工具（x64 和 x86）](/zh-cn/shows/defrag-tools/building-your-usb-thumbdrive)
- [调试内核模式故障内存转储](/zh-cn/shows/defrag-tools/defragtools-137-debugging-kernel-mode-dumps)
- [特殊池](https://www.youtube.com/watch?v=vHXYS9KdU1k)

## 使用驱动程序验证程序进行高级故障排除

我们估计，大约 75% 的所有停止错误是由有故障的驱动程序引起的。 驱动程序验证程序工具提供了多种方法来帮助你进行故障排除。 其中包括在隔离内存池中运行驱动程序（不与其他组件共享内存）、生成极端内存压力和验证参数。 如果工具在执行驱动程序代码时遇到错误，它会主动创建异常。 然后，它可以进一步检查代码的这一部分。

警告

驱动程序验证程序消耗大量 CPU，可能会显著降低计算机速度。 你还可能会遇到更多崩溃。 验证程序在发生停止错误后禁用故障驱动程序，并继续执行此作，直到可以成功重启系统并访问桌面。 你还可以预计会看到多个转储文件被创建。

不要一次尝试验证所有驱动程序。 此作可能会降低性能，并使系统不可用。 它还会限制工具的有效性。

使用驱动程序验证程序时，请使用以下准则：

- 测试任何“可疑”驱动程序。 例如，最近更新的驱动程序或已知有问题的驱动程序。
- 如果继续遇到不可分析的崩溃，请尝试在所有第三方和未签名的驱动程序上启用验证。
- 对 10-20 个驱动程序组启用并发验证。
- 此外，如果计算机由于驱动程序验证程序而无法启动到桌面，可以通过在安全模式下启动来禁用该工具。 此解决方案是因为该工具无法在安全模式下运行。

有关详细信息，请参阅[驱动程序验证程序](/zh-cn/windows-hardware/drivers/devtest/driver-verifier)。

## 常见的 Windows 停止错误

本部分不包含所有错误代码的列表，但由于许多错误代码具有相同的潜在解决方法，因此最好按照以下步骤排查错误。 有关停止错误代码的完整列表，请参阅 [Bug 检查代码参考](/zh-cn/windows-hardware/drivers/debugger/bug-check-code-reference2)。

以下部分列出了常见停止错误代码的常规故障排除过程。

### VIDEO\_ENGINE\_TIMEOUT\_DETECTED或VIDEO\_TDR\_TIMEOUT\_DETECTED

停止错误代码0x00000141或0x00000117

请联系列出的显示驱动程序的供应商，获取该驱动程序的相应更新。

### DRIVER\_IRQL\_NOT\_LESS\_OR\_EQUAL（驱动程序中断请求级别错误）

停止错误代码0x0000000D1

通过从Microsoft更新目录网站为系统应用最新的累积更新，来确保驱动程序获得最新更新。 更新过时的网络驱动程序。 虚拟化 VMware 系统通常运行“Intel（R） PRO/1000 MT 网络连接”（e1g6032e.sys）。 可以从 [Intel 下载驱动程序和软件网站](https://downloadcenter.intel.com)下载此驱动程序。 请联系硬件供应商更新网络驱动程序以获取解决方案。 对于 VMware 系统，请使用 VMware 集成网络驱动程序，而不是 Intel 的 e1g6032e.sys。 例如，使用 VMware 类型 VMXNET、VMXNET2 或VMXNET3。

### PAGE\_FAULT\_IN\_NONPAGED\_AREA

停止错误代码0x000000050

如果在停止错误消息中标识了驱动程序，请与制造商联系以获取更新。 如果没有可用的更新，请禁用驱动程序，并监视系统是否稳定。 运行 `chkdsk /f /r` 以检测和修复磁盘错误。 在磁盘扫描开始于系统分区之前重启系统。 请联系制造商，获取它们可能为硬盘子系统提供的任何诊断工具。 尝试重新安装最近安装或更新的任何应用程序或服务。 当系统启动应用程序并读取注册表以获取首选项设置时，可能会触发崩溃。 重新安装应用程序可以修复损坏的注册表项。 如果问题仍然存在，并且您已经运行了最近的系统状态备份，请尝试从备份中还原注册表配置单元。

### SYSTEM\_SERVICE\_EXCEPTION

停止错误代码 c000021a {致命系统错误} Windows SubSystem 系统进程意外终止，状态为0xc0000005。 系统已关闭。

使用系统文件检查器工具修复丢失或损坏的系统文件。 系统文件检查器允许用户扫描 Windows 系统文件中的损坏并还原损坏的文件。 有关详细信息，请参阅 [“使用系统文件检查器”工具](https://support.microsoft.com/topic/use-the-system-file-checker-tool-to-repair-missing-or-corrupted-system-files-79aa86cb-ca52-166a-92a3-966e85d4094e)。

### NTFS\_FILE\_SYSTEM

停止错误代码0x000000024

此停止错误通常是由硬盘上的 NTFS 文件系统损坏或损坏块（扇区）引起的。 硬盘（SATA 或 IDE）损坏的驱动程序也会对系统读取和写入磁盘的能力产生不利影响。 运行存储子系统制造商提供的任何硬件诊断。 使用扫描磁盘工具验证没有文件系统错误。 若要执行此步骤，请右键单击要扫描的驱动器，选择“属性”，选择“工具”，然后选择“立即检查”按钮。 更新 NTFS 文件系统驱动程序（Ntfs.sys）。 为当前遇到问题的操作系统应用最新的累积更新。

### KMODE\_EXCEPTION\_NOT\_HANDLED

停止错误代码0x0000001E

如果在停止错误消息中标识了驱动程序，请禁用或删除该驱动程序。 禁用或删除最近添加的所有驱动程序或服务。

如果在启动序列期间发生错误，并且系统分区是使用 NTFS 文件系统格式化的，则可以使用安全模式在 Device Manager 中禁用驱动程序。 若要禁用驱动程序，请执行以下步骤：

1. 转到“设置”“更新与安全”>“恢复”>。
2. 在“高级启动”下，选择“立即重启”。
3. 在电脑重启显示“选择选项”屏幕后，选择“故障排除”“高级选项”“启动设置”>“重启”>>。
4. 计算机重启后，将显示选项列表。 按 4 或 F4 以安全模式启动计算机。 如果打算在安全模式下使用互联网，请按 5 或 F5 选择 **带网络连接的安全模式** 选项。

### DPC\_WATCHDOG\_VIOLATION

停止错误代码0x00000133

此停止错误代码是由在某些条件下未在分配的时间范围内完成其工作的故障驱动程序引起的。 为了帮助缓解此错误，请从系统收集内存转储文件，然后使用 Windows 调试器查找故障驱动程序。 如果在停止错误消息中标识了驱动程序，请禁用驱动程序以隔离问题。 请与制造商联系以获取驱动程序更新。 在事件查看器中检查系统日志，了解可能有助于识别导致停止错误0x133的设备或驱动程序的其他错误消息。 验证安装的任何新硬件是否与安装的 Windows 版本兼容。 例如，可以在 Windows 10 规范中获取有关所需硬件的信息。 如果安装了 Windows 调试器，并且你有权访问公共符号，则可以将 *c：\windows\memory.dmp* 文件加载到调试器中。 然后，请参阅 [在 Windows Server 2012 上确定 Bug 检查 0x133（DPC\_WATCHDOG\_VIOLATION）错误的来源](/zh-cn/archive/blogs/ntdebugging/determining-the-source-of-bug-check-0x133-dpc_watchdog_violation-errors-on-windows-server-2012)，以便从内存转储中识别出有问题的驱动程序。

### 用户模式健康监视器

停止错误代码0x0000009E

此停止错误表示用户模式运行状况检查失败，从而阻止正常关闭。 Windows 通过重启或启用应用程序故障转移到其他服务器来还原关键服务。 群集服务包含检测机制，可在用户模式组件中检测无响应。

此停止错误通常发生在群集环境中，被指示为故障的驱动程序是 RHS.exe。 检查事件日志中是否存在任何存储故障，以确定失败的进程。 尝试更新事件日志中指示的组件或进程。 应该看到以下事件记录：

- 事件 ID：4870
- 源：Microsoft-Windows-FailoverClustering
- 说明：用户模式运行状况监视检测到系统未响应。 故障转移群集虚拟适配器与群集服务器进程失去联系，其进程 ID 为“%1”，为“%2”秒。 已执行恢复措施。 检查集群日志以识别相关的进程，并分析哪些项可能导致进程挂起。

有关详细信息，请参阅 [基于 Windows Server 的多节点故障转移群集环境中的群集节点上的“0x0000009E”停止错误](https://support.microsoft.com/topic/-0x0000009e-stop-error-on-cluster-nodes-in-a-windows-server-based-multi-node-failover-cluster-environment-7e0acceb-b498-47f8-e004-96de6e497cba)，请同时查看以下微软视频 [如果发生 9E 错误时该怎么办](https://www.youtube.com/watch?v=vOJQEdmdSgw)。

## 调试示例

### 示例 1

此错误检查是由驱动程序在升级期间挂起引起的，导致在Microsoft驱动程序*NDIS.sys*中发生D1错误检查。 IMAGE\_NAME会告诉你有故障的驱动程序，但由于此驱动程序是Microsoft驱动程序，因此无法替换或删除该驱动程序。 解决方法是在设备管理器中禁用网络设备，然后再次尝试升级。

```
2: kd> !analyze -v
*******************************************************************************
*                                                                             *
*                        Bugcheck Analysis                                    *
*                                                                             *
*******************************************************************************

DRIVER_IRQL_NOT_LESS_OR_EQUAL (d1)
An attempt was made to access a pageable (or completely invalid) address at an
interrupt request level (IRQL) that is too high.  This is usually
caused by drivers using improper addresses.
If kernel debugger is available get stack backtrace.
Arguments:
Arg1: 000000000011092a, memory referenced
Arg2: 0000000000000002, IRQL
Arg3: 0000000000000001, value 0 = read operation, 1 = write operation
Arg4: fffff807aa74f4c4, address which referenced memory
Debugging Details:
------------------

KEY_VALUES_STRING: 1
STACKHASH_ANALYSIS: 1
TIMELINE_ANALYSIS: 1
DUMP_CLASS: 1
DUMP_QUALIFIER: 400
SIMULTANEOUS_TELSVC_INSTANCES:  0
SIMULTANEOUS_TELWP_INSTANCES:  0
BUILD_VERSION_STRING:  16299.15.amd64fre.rs3_release.170928-1534
SYSTEM_MANUFACTURER:  Alienware
SYSTEM_PRODUCT_NAME:  Alienware 15 R2
SYSTEM_SKU:  Alienware 15 R2
SYSTEM_VERSION:  1.2.8
BIOS_VENDOR:  Alienware
BIOS_VERSION:  1.2.8
BIOS_DATE:  01/29/2016
BASEBOARD_MANUFACTURER:  Alienware
BASEBOARD_PRODUCT:  Alienware 15 R2
BASEBOARD_VERSION:  A00
DUMP_TYPE:  2
BUGCHECK_P1: 11092a
BUGCHECK_P2: 2
BUGCHECK_P3: 1
BUGCHECK_P4: fffff807aa74f4c4
WRITE_ADDRESS: fffff80060602380: Unable to get MiVisibleState
Unable to get NonPagedPoolStart
Unable to get NonPagedPoolEnd
Unable to get PagedPoolStart
Unable to get PagedPoolEnd
000000000011092a
CURRENT_IRQL:  2
FAULTING_IP:
NDIS!NdisQueueIoWorkItem+4 [minio\ndis\sys\miniport.c @ 9708]
fffff807`aa74f4c4 48895120        mov     qword ptr [rcx+20h],rdx
CPU_COUNT: 8
CPU_MHZ: a20
CPU_VENDOR:  GenuineIntel
CPU_FAMILY: 6
CPU_MODEL: 5e
CPU_STEPPING: 3
CPU_MICROCODE: 6,5e,3,0 (F,M,S,R)  SIG: BA'00000000 (cache) BA'00000000 (init)
BLACKBOXPNP: 1 (!blackboxpnp)
DEFAULT_BUCKET_ID:  WIN8_DRIVER_FAULT
BUGCHECK_STR:  AV
PROCESS_NAME:  System
ANALYSIS_SESSION_HOST:  SHENDRIX-DEV0
ANALYSIS_SESSION_TIME:  01-17-2019 11:06:05.0653
ANALYSIS_VERSION: 10.0.18248.1001 amd64fre
TRAP_FRAME:  ffffa884c0c3f6b0 -- (.trap 0xffffa884c0c3f6b0)
NOTE: The trap frame doesn't contain all registers.
Some register values may be zeroed or incorrect.
rax=fffff807ad018bf0 rbx=0000000000000000 rcx=000000000011090a
rdx=fffff807ad018c10 rsi=0000000000000000 rdi=0000000000000000
rip=fffff807aa74f4c4 rsp=ffffa884c0c3f840 rbp=000000002408fd00
r8=ffffb30e0e99ea30  r9=0000000001d371c1 r10=0000000020000080
r11=0000000000000000 r12=0000000000000000 r13=0000000000000000
r14=0000000000000000 r15=0000000000000000
iopl=0         nv up ei ng nz na pe nc
NDIS!NdisQueueIoWorkItem+0x4:
fffff807`aa74f4c4 48895120        mov     qword ptr [rcx+20h],rdx ds:00000000`0011092a=????????????????
Resetting default scope

LAST_CONTROL_TRANSFER:  from fffff800603799e9 to fffff8006036e0e0

STACK_TEXT:
ffffa884`c0c3f568 fffff800`603799e9 : 00000000`0000000a 00000000`0011092a 00000000`00000002 00000000`00000001 : nt!KeBugCheckEx [minkernel\ntos\ke\amd64\procstat.asm @ 134]
ffffa884`c0c3f570 fffff800`60377d7d : fffff78a`4000a150 ffffb30e`03fba001 ffff8180`f0b5d180 00000000`000000ff : nt!KiBugCheckDispatch+0x69 [minkernel\ntos\ke\amd64\trap.asm @ 2998]
ffffa884`c0c3f6b0 fffff807`aa74f4c4 : 00000000`00000002 ffff8180`f0754180 00000000`00269fb1 ffff8180`f0754180 : nt!KiPageFault+0x23d [minkernel\ntos\ke\amd64\trap.asm @ 1248]
ffffa884`c0c3f840 fffff800`60256b63 : ffffb30e`0e18f710 ffff8180`f0754180 ffffa884`c0c3fa18 00000000`00000002 : NDIS!NdisQueueIoWorkItem+0x4 [minio\ndis\sys\miniport.c @ 9708]
ffffa884`c0c3f870 fffff800`60257bfd : 00000000`00000008 00000000`00000000 00000000`00269fb1 ffff8180`f0754180 : nt!KiProcessExpiredTimerList+0x153 [minkernel\ntos\ke\dpcsup.c @ 2078]
ffffa884`c0c3f960 fffff800`6037123a : 00000000`00000000 ffff8180`f0754180 00000000`00000000 ffff8180`f0760cc0 : nt!KiRetireDpcList+0x43d [minkernel\ntos\ke\dpcsup.c @ 1512]
ffffa884`c0c3fb60 00000000`00000000 : ffffa884`c0c40000 ffffa884`c0c39000 00000000`00000000 00000000`00000000 : nt!KiIdleLoop+0x5a [minkernel\ntos\ke\amd64\idle.asm @ 166]

RETRACER_ANALYSIS_TAG_STATUS:  Failed in getting KPCR for core 2
THREAD_SHA1_HASH_MOD_FUNC:  5b59a784f22d4b5cbd5a8452fe39914b8fd7961d
THREAD_SHA1_HASH_MOD_FUNC_OFFSET:  5643383f9cae3ca39073f7721b53f0c633bfb948
THREAD_SHA1_HASH_MOD:  20edda059578820e64b723e466deea47f59bd675
FOLLOWUP_IP:
NDIS!NdisQueueIoWorkItem+4 [minio\ndis\sys\miniport.c @ 9708]
fffff807`aa74f4c4 48895120        mov     qword ptr [rcx+20h],rdx
FAULT_INSTR_CODE:  20518948
FAULTING_SOURCE_LINE:  minio\ndis\sys\miniport.c
FAULTING_SOURCE_FILE:  minio\ndis\sys\miniport.c
FAULTING_SOURCE_LINE_NUMBER:  9708
FAULTING_SOURCE_CODE:
  9704:     _In_ _Points_to_data_      PVOID                       WorkItemContext
  9705:     )
  9706: {
  9707:
> 9708:     ((PNDIS_IO_WORK_ITEM)NdisIoWorkItemHandle)->Routine = Routine;
  9709:     ((PNDIS_IO_WORK_ITEM)NdisIoWorkItemHandle)->WorkItemContext = WorkItemContext;
  9710:
  9711:     IoQueueWorkItem(((PNDIS_IO_WORK_ITEM)NdisIoWorkItemHandle)->IoWorkItem,
  9712:                     ndisDispatchIoWorkItem,
  9713:                     CriticalWorkQueue,

SYMBOL_STACK_INDEX:  3
SYMBOL_NAME:  NDIS!NdisQueueIoWorkItem+4
FOLLOWUP_NAME:  ndiscore
MODULE_NAME: NDIS
IMAGE_NAME:  NDIS.SYS
DEBUG_FLR_IMAGE_TIMESTAMP:  0
IMAGE_VERSION:  10.0.16299.99
DXGANALYZE_ANALYSIS_TAG_PORT_GLOBAL_INFO_STR:  Hybrid_FALSE
DXGANALYZE_ANALYSIS_TAG_ADAPTER_INFO_STR:  GPU0_VenId0x1414_DevId0x8d_WDDM1.3_Active;
STACK_COMMAND:  .thread ; .cxr ; kb
BUCKET_ID_FUNC_OFFSET:  4
FAILURE_BUCKET_ID:  AV_NDIS!NdisQueueIoWorkItem
BUCKET_ID:  AV_NDIS!NdisQueueIoWorkItem
PRIMARY_PROBLEM_CLASS:  AV_NDIS!NdisQueueIoWorkItem
TARGET_TIME:  2017-12-10T14:16:08.000Z
OSBUILD:  16299
OSSERVICEPACK:  98
SERVICEPACK_NUMBER: 0
OS_REVISION: 0
SUITE_MASK:  784
PRODUCT_TYPE:  1
OSPLATFORM_TYPE:  x64
OSNAME:  Windows 10
OSEDITION:  Windows 10 WinNt TerminalServer SingleUserTS Personal
OS_LOCALE:
USER_LCID:  0
OSBUILD_TIMESTAMP:  2017-11-26 03:49:20
BUILDDATESTAMP_STR:  170928-1534
BUILDLAB_STR:  rs3_release
BUILDOSVER_STR:  10.0.16299.15.amd64fre.rs3_release.170928-1534
ANALYSIS_SESSION_ELAPSED_TIME:  8377
ANALYSIS_SOURCE:  KM
FAILURE_ID_HASH_STRING:  km:av_ndis!ndisqueueioworkitem
FAILURE_ID_HASH:  {10686423-afa1-4852-ad1b-9324ac44ac96}
FAILURE_ID_REPORT_LINK: https://go.microsoft.com/fwlink/?LinkID=397724&FailureHash=10686423-afa1-4852-ad1b-9324ac44ac96
Followup:     ndiscore
---------
```

### 示例 2

在此示例中，非Microsoft驱动程序导致页面错误，因此我们没有此驱动程序的符号。 但是，查看IMAGE\_NAME和或MODULE\_NAME表明是*WwanUsbMP.sys*导致了此问题。 断开设备连接并重试升级是一种可能的解决方案。

```
1: kd> !analyze -v
*******************************************************************************
*                                                                             *
*                        Bugcheck Analysis                                    *
*                                                                             *
*******************************************************************************

PAGE_FAULT_IN_NONPAGED_AREA (50)
Invalid system memory was referenced.  This can't be protected by try-except.
Typically the address is just plain bad or it is pointing at freed memory.
Arguments:
Arg1: 8ba10000, memory referenced.
Arg2: 00000000, value 0 = read operation, 1 = write operation.
Arg3: 82154573, If non-zero, the instruction address which referenced the bad memory
                address.
Arg4: 00000000, (reserved)

Debugging Details:
------------------

*** WARNING: Unable to verify timestamp for WwanUsbMp.sys
*** ERROR: Module load completed but symbols could not be loaded for WwanUsbMp.sys

KEY_VALUES_STRING: 1
STACKHASH_ANALYSIS: 1
TIMELINE_ANALYSIS: 1
DUMP_CLASS: 1
DUMP_QUALIFIER: 400
BUILD_VERSION_STRING:  16299.15.x86fre.rs3_release.170928-1534
MARKER_MODULE_NAME:  IBM_ibmpmdrv
SYSTEM_MANUFACTURER:  LENOVO
SYSTEM_PRODUCT_NAME:  20AWS07H00
SYSTEM_SKU:  LENOVO_MT_20AW_BU_Think_FM_ThinkPad T440p
SYSTEM_VERSION:  ThinkPad T440p
BIOS_VENDOR:  LENOVO
BIOS_VERSION:  GLET85WW (2.39 )
BIOS_DATE:  09/29/2016
BASEBOARD_MANUFACTURER:  LENOVO
BASEBOARD_PRODUCT:  20AWS07H00
BASEBOARD_VERSION:  Not Defined
DUMP_TYPE:  2
BUGCHECK_P1: ffffffff8ba10000
BUGCHECK_P2: 0
BUGCHECK_P3: ffffffff82154573
BUGCHECK_P4: 0
READ_ADDRESS: 822821d0: Unable to get MiVisibleState
8ba10000
FAULTING_IP:
nt!memcpy+33 [minkernel\crts\crtw32\string\i386\memcpy.asm @ 213
82154573 f3a5            rep movs dword ptr es:[edi],dword ptr [esi]
MM_INTERNAL_CODE:  0
CPU_COUNT: 4
CPU_MHZ: 95a
CPU_VENDOR:  GenuineIntel
CPU_FAMILY: 6
CPU_MODEL: 3c
CPU_STEPPING: 3
CPU_MICROCODE: 6,3c,3,0 (F,M,S,R)  SIG: 21'00000000 (cache) 21'00000000 (init)
BLACKBOXBSD: 1 (!blackboxbsd)
BLACKBOXPNP: 1 (!blackboxpnp)
DEFAULT_BUCKET_ID:  WIN8_DRIVER_FAULT
BUGCHECK_STR:  AV
PROCESS_NAME:  System
CURRENT_IRQL:  2
ANALYSIS_SESSION_HOST:  SHENDRIX-DEV0
ANALYSIS_SESSION_TIME:  01-17-2019 10:54:53.0780
ANALYSIS_VERSION: 10.0.18248.1001 amd64fre
TRAP_FRAME:  8ba0efa8 -- (.trap 0xffffffff8ba0efa8)
ErrCode = 00000000
eax=8ba1759e ebx=a2bfd314 ecx=00001d67 edx=00000002 esi=8ba10000 edi=a2bfe280
eip=82154573 esp=8ba0f01c ebp=8ba0f024 iopl=0         nv up ei pl nz ac pe nc
cs=0008  ss=0010  ds=0023  es=0023  fs=0030  gs=0000             efl=00010216
nt!memcpy+0x33:
82154573 f3a5            rep movs dword ptr es:[edi],dword ptr [esi]
Resetting default scope
LOCK_ADDRESS:  8226c6e0 -- (!locks 8226c6e0)
Cannot get _ERESOURCE type
Resource @ nt!PiEngineLock (0x8226c6e0)    Available
1 total locks
PNP_TRIAGE_DATA:
                Lock address  : 0x8226c6e0
                Thread Count  : 0
                Thread address: 0x00000000
                Thread wait   : 0x0

LAST_CONTROL_TRANSFER:  from 82076708 to 821507e8

STACK_TEXT:
8ba0ede4 82076708 00000050 8ba10000 00000000 nt!KeBugCheckEx [minkernel\ntos\ke\i386\procstat.asm @ 114]
8ba0ee40 8207771e 8ba0efa8 8ba10000 8ba0eea0 nt!MiSystemFault+0x13c8 [minkernel\ntos\mm\mmfault.c @ 4755]
8ba0ef08 821652ac 00000000 8ba10000 00000000 nt!MmAccessFault+0x83e [minkernel\ntos\mm\mmfault.c @ 6868]
8ba0ef08 82154573 00000000 8ba10000 00000000 nt!_KiTrap0E+0xec [minkernel\ntos\ke\i386\trap.asm @ 5153]
8ba0f024 86692866 a2bfd314 8ba0f094 0000850a nt!memcpy+0x33 [minkernel\crts\crtw32\string\i386\memcpy.asm @ 213]
8ba0f040 866961bc 8ba0f19c a2bfd0e8 00000000 NDIS!ndisMSetPowerManagementCapabilities+0x8a [minio\ndis\sys\miniport.c @ 7969]
8ba0f060 866e1f66 866e1caf adfb9000 00000000 NDIS!ndisMSetGeneralAttributes+0x23d [minio\ndis\sys\miniport.c @ 8198]
8ba0f078 ac50c15f a2bfd0e8 0000009f 00000001 NDIS!NdisMSetMiniportAttributes+0x2b7 [minio\ndis\sys\miniport.c @ 7184]
WARNING: Stack unwind information not available. Following frames may be wrong.
8ba0f270 ac526f96 adfb9000 a2bfd0e8 8269b9b0 WwanUsbMp+0x1c15f
8ba0f3cc 866e368a a2bfd0e8 00000000 8ba0f4c0 WwanUsbMp+0x36f96
8ba0f410 867004b0 a2bfd0e8 a2bfd0e8 a2be2a70 NDIS!ndisMInvokeInitialize+0x60 [minio\ndis\sys\miniport.c @ 13834]
8ba0f7ac 866dbc8e a2acf730 866b807c 00000000 NDIS!ndisMInitializeAdapter+0xa23 [minio\ndis\sys\miniport.c @ 601]
8ba0f7d8 866e687d a2bfd0e8 00000000 00000000 NDIS!ndisInitializeAdapter+0x4c [minio\ndis\sys\initpnp.c @ 931]
8ba0f800 866e90bb adfb64d8 00000000 a2bfd0e8 NDIS!ndisPnPStartDevice+0x118 [minio\ndis\sys\configm.c @ 4235]
8ba0f820 866e8a58 adfb64d8 a2bfd0e8 00000000 NDIS!ndisStartDeviceSynchronous+0xbd [minio\ndis\sys\ndispnp.c @ 3096]
8ba0f838 866e81df adfb64d8 8ba0f85e 8ba0f85f NDIS!ndisPnPIrpStartDevice+0xb4 [minio\ndis\sys\ndispnp.c @ 1067]
8ba0f860 820a7e98 a2bfd030 adfb64d8 8ba0f910 NDIS!ndisPnPDispatch+0x108 [minio\ndis\sys\ndispnp.c @ 2429]
8ba0f878 8231f07e 8ba0f8ec adf5d4c8 872e2eb8 nt!IofCallDriver+0x48 [minkernel\ntos\io\iomgr\iosubs.c @ 3149]
8ba0f898 820b8569 820c92b8 872e2eb8 8ba0f910 nt!PnpAsynchronousCall+0x9e [minkernel\ntos\io\pnpmgr\irp.c @ 3005]
8ba0f8cc 820c9a76 00000000 820c92b8 872e2eb8 nt!PnpSendIrp+0x67 [minkernel\ntos\io\pnpmgr\irp.h @ 286]
8ba0f914 8234577b 872e2eb8 adf638b0 adf638b0 nt!PnpStartDevice+0x60 [minkernel\ntos\io\pnpmgr\irp.c @ 3187]
8ba0f94c 82346cc7 872e2eb8 adf638b0 adf638b0 nt!PnpStartDeviceNode+0xc3 [minkernel\ntos\io\pnpmgr\start.c @ 1712]
8ba0f96c 82343c68 00000000 a2bdb3d8 adf638b0 nt!PipProcessStartPhase1+0x4d [minkernel\ntos\io\pnpmgr\start.c @ 114]
8ba0fb5c 824db885 8ba0fb80 00000000 00000000 nt!PipProcessDevNodeTree+0x386 [minkernel\ntos\io\pnpmgr\enum.c @ 6129]
8ba0fb88 8219571b 85852520 8c601040 8226ba90 nt!PiRestartDevice+0x91 [minkernel\ntos\io\pnpmgr\enum.c @ 4743]
8ba0fbe8 820804af 00000000 00000000 8c601040 nt!PnpDeviceActionWorker+0xdb4b7 [minkernel\ntos\io\pnpmgr\action.c @ 674]
8ba0fc38 8211485c 85852520 421de295 00000000 nt!ExpWorkerThread+0xcf [minkernel\ntos\ex\worker.c @ 4270]
8ba0fc70 82166785 820803e0 85852520 00000000 nt!PspSystemThreadStartup+0x4a [minkernel\ntos\ps\psexec.c @ 7756]
8ba0fc88 82051e07 85943940 8ba0fcd8 82051bb9 nt!KiThreadStartup+0x15 [minkernel\ntos\ke\i386\threadbg.asm @ 82]
8ba0fc94 82051bb9 8b9cc600 8ba10000 8ba0d000 nt!KiProcessDeferredReadyList+0x17 [minkernel\ntos\ke\thredsup.c @ 5309]
8ba0fcd8 00000000 00000000 00000000 00000000 nt!KeSetPriorityThread+0x249 [minkernel\ntos\ke\thredobj.c @ 3881]

RETRACER_ANALYSIS_TAG_STATUS:  Failed in getting KPCR for core 1
THREAD_SHA1_HASH_MOD_FUNC:  e029276c66aea80ba36903e89947127118d31128
THREAD_SHA1_HASH_MOD_FUNC_OFFSET:  012389f065d31c8eedd6204846a560146a38099b
THREAD_SHA1_HASH_MOD:  44dc639eb162a28d47eaeeae4afe6f9eeccced3d
FOLLOWUP_IP:
WwanUsbMp+1c15f
ac50c15f 8bf0            mov     esi,eax
FAULT_INSTR_CODE:  f33bf08b
SYMBOL_STACK_INDEX:  8
SYMBOL_NAME:  WwanUsbMp+1c15f
FOLLOWUP_NAME:  MachineOwner
MODULE_NAME: WwanUsbMp
IMAGE_NAME:  WwanUsbMp.sys
DEBUG_FLR_IMAGE_TIMESTAMP:  5211bb0c
DXGANALYZE_ANALYSIS_TAG_PORT_GLOBAL_INFO_STR:  Hybrid_FALSE
DXGANALYZE_ANALYSIS_TAG_ADAPTER_INFO_STR:  GPU0_VenId0x1414_DevId0x8d_WDDM1.3_NotActive;GPU1_VenId0x8086_DevId0x416_WDDM1.3_Active_Post;
STACK_COMMAND:  .thread ; .cxr ; kb
BUCKET_ID_FUNC_OFFSET:  1c15f
FAILURE_BUCKET_ID:  AV_R_INVALID_WwanUsbMp!unknown_function
BUCKET_ID:  AV_R_INVALID_WwanUsbMp!unknown_function
PRIMARY_PROBLEM_CLASS:  AV_R_INVALID_WwanUsbMp!unknown_function
TARGET_TIME:  2018-02-12T11:33:51.000Z
OSBUILD:  16299
OSSERVICEPACK:  15
SERVICEPACK_NUMBER: 0
OS_REVISION: 0
SUITE_MASK:  272
PRODUCT_TYPE:  1
OSPLATFORM_TYPE:  x86
OSNAME:  Windows 10
OSEDITION:  Windows 10 WinNt TerminalServer SingleUserTS
OS_LOCALE:
USER_LCID:  0
OSBUILD_TIMESTAMP:  2017-09-28 18:32:28
BUILDDATESTAMP_STR:  170928-1534
BUILDLAB_STR:  rs3_release
BUILDOSVER_STR:  10.0.16299.15.x86fre.rs3_release.170928-1534
ANALYSIS_SESSION_ELAPSED_TIME:  162bd
ANALYSIS_SOURCE:  KM
FAILURE_ID_HASH_STRING:  km:av_r_invalid_wwanusbmp!unknown_function
FAILURE_ID_HASH:  {31e4d053-0758-e43a-06a7-55f69b072cb3}
FAILURE_ID_REPORT_LINK: https://go.microsoft.com/fwlink/?LinkID=397724&FailureHash=31e4d053-0758-e43a-06a7-55f69b072cb3

Followup:     MachineOwner
---------

ReadVirtual: 812d1248 not properly sign extended
```

## 参考文献

[错误检查代码参考](/zh-cn/windows-hardware/drivers/debugger/bug-check-code-reference2)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/stop-code-error-troubleshooting)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
