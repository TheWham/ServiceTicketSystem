# Windows 启动问题的高级故障排除

[**试用我们的虚拟代理**](https://vsa.services.microsoft.com/v1.0/?partnerId=7d74cf73-5217-4008-833f-87a1a278f2cb&flowId=DMC&initialQuery=boot)- 它可以帮助你快速识别和修复常见的 Windows 搜索问题。

## 摘要

本文可帮助你诊断和修复阻止 Windows 正确启动的问题。 本文讨论了启动过程的不同阶段（PreBoot、启动管理器、OS 加载程序或内核），以及如何确定受影响的阶段。 对于每个阶段，本文提供了可用于识别和修复启动问题的工具的分步指南和简介。

注意

本文适用于支持代理和 IT 专业人员。 如果要查找有关恢复选项的更多常规信息，请参阅 [Windows 10 中的恢复选项](https://support.microsoft.com/windows/recovery-options-in-windows-31ce2444-7de3-818c-d626-e3b5a3024da5)。

## 启动过程的阶段

在启动过程中，基于 Windows 的计算机可能存在问题的原因有多种。

若要排查启动问题，请首先确定计算机卡住以下阶段中的哪一个阶段：

| 阶段 | 流程 | 基于 BIOS 的计算机 | 基于 UEFI 的计算机 |
| --- | --- | --- | --- |
| 1 | 预启动 | MBR/PBR（启动代码） | UEFI 固件 |
| 2 | Windows 引导管理器 | %SystemDrive%\bootmgr | \EFI\Microsoft\Boot\bootmgfw.efi |
| 3 | Windows OS 加载程序 | %SystemRoot%\system32\winload.exe | %SystemRoot%\system32\winload.efi |
| 4 | Windows NT OS 内核 | %SystemRoot%\system32\ntoskrnl.exe |  |

1. **PreBoot 进程：** 电脑的固件启动开机自测试（POST）并加载固件设置。 当固件检测到有效的系统磁盘时，此过程将结束。

   - 当基于 BIOS 的计算机进入此阶段时，固件会将主启动记录（MBR）加载到内存中，然后启动 Windows 启动管理器。
   - 当基于 UEFI 的计算机进入此阶段时，固件将加载并启动 Windows 启动管理器 EFI 应用程序。
2. **Windows 启动管理器：** Windows 启动管理器在 Windows 启动分区上查找 Windows 加载程序（Winload.exe），然后启动它。
3. **Windows作系统加载程序：** Windows 加载程序加载 Windows 内核所需的驱动程序，然后启动内核。
4. **Windows NT OS 内核：** 内核将系统注册表配置单元加载到内存中。 它还加载标记为 `BOOT_START`其他驱动程序。

   内核将控制权传递给会话管理器进程（Smss.exe）。 此过程初始化系统会话，然后加载并启动未标记为 `BOOT_START`“的设备”和“驱动程序”。

下图显示了启动序列、显示内容以及序列中该点的典型启动问题。 在开始故障排除之前，必须了解启动过程的大纲和显示状态，以确保在参与开始时正确识别问题。 选择缩略图可进行放大显示。

[![启动序列流程图图解。](media/windows-boot-issues-troubleshooting/boot-sequence-thumb.png)](media/windows-boot-issues-troubleshooting/boot-sequence-thumb-expanded.png#lightbox)

每个阶段都对应不同的疑难解答方法。 本文提供前三个阶段中发生的问题的故障排除技术。

注意

如果计算机在恢复选项显示时反复停止启动进程，请在命令提示符处运行以下命令以中断周期：

`Bcdedit /set {default} recoveryenabled no`

如果 F8 选项不起作用，请运行以下命令：

`Bcdedit /set {default} bootmenupolicy legacy`

## 排查 BIOS 阶段的问题

若要确定系统是否已通过 BIOS 阶段，请执行以下步骤：

1. 如果有任何外部外围设备连接到计算机，请断开它们的连接。
2. 检查物理计算机上的硬盘驱动器指示灯是否正常工作。 如果不工作，则此故障指示启动进程卡在 BIOS 阶段。
3. 按 NumLock 键以查看指示灯是否打开和关闭。 如果未切换，此功能失调表明启动过程停滞在 BIOS 阶段。

   如果系统停滞在 BIOS 阶段，则可能存在硬件问题。

## 诊断启动加载程序阶段的问题

如果屏幕为黑色（闪烁光标除外）或收到以下错误代码之一，则启动进程停滞在启动加载程序阶段：

- `Boot Configuration Data (BCD) missing or corrupted`
- `Boot file or MBR corrupted`
- `Operating system Missing`
- `Boot sector missing or corrupted`
- `Bootmgr missing or corrupted`
- `Unable to boot due to system hive missing or corrupted`

若要解决此问题，请使用 Windows 安装媒体启动计算机，按 Shift+F10 进行命令提示符，然后使用以下任一方法。

### 方法 1：使用启动修复工具

启动修复工具会自动修复许多常见问题。 该工具还允许快速诊断和修复更复杂的启动问题。 当计算机检测到启动问题时，计算机将启动启动修复工具。 该工具启动时，它会执行诊断。 这些诊断包括分析启动日志文件以确定问题的原因。 启动修复工具确定原因时，该工具会尝试自动修复问题。

要执行此调用启动修复工具的任务，请执行以下步骤。

注意

有关启动 WinRE 的其他方法，请参阅 [Windows 恢复环境 (Windows RE)](/zh-cn/windows-hardware/manufacture/desktop/windows-recovery-environment--windows-re--technical-reference#entry-points-into-winre)。

1. 将系统启动到已安装版本的 Windows 的安装媒体。 有关更多信息，请参阅[针对 Windows 创建安装介质](https://support.microsoft.com/windows/create-installation-media-for-windows-99a58364-8c02-206f-aa6f-40c3b507420d)。
2. 在“安装 Windows”屏幕上，选择“下一步”>“修复计算机”。
3. 在“选择一个选项”屏幕上，选择“疑难解答”。
4. 在“高级选项”屏幕上，选择“启动修复”。
5. 启动修复后，选择“ **关闭**”，然后打开电脑以查看 Windows 是否可以正常启动。

启动修复工具会生成一个日志文件，以帮助你了解启动问题和已进行的修复。 可以在 %windir%\System32\LogFiles\Srt\Srttrail.txt 文件夹中找到日志文件

有关详细信息，请参阅[对蓝屏错误进行疑难解答](https://support.microsoft.com/sbs/windows/troubleshoot-blue-screen-errors-5c62726c-6489-52da-a372-3f73142c14ad)。

### 方法 2：修复启动代码

要修复启动代码，请运行以下命令：

```
BOOTREC /FIXMBR
```

要修复启动扇区，请运行以下命令：

```
BOOTREC /FIXBOOT
```

注意

同时运行 `BOOTREC` 和 `Fixmbr` 仅覆盖主启动代码。 如果 MBR 中的损坏会影响分区表，则运行 `Fixmbr` 可能无法解决问题。

### 方法 3：修复 BCD 错误

如果收到与 BCD 相关的错误，请执行以下步骤：

1. 扫描安装的所有系统。 要执行此步骤，请运行以下命令：

   ```
   Bootrec /ScanOS
   ```
2. 若要检查问题是否已修复，请重新启动计算机。
3. 如果问题未修复，请运行以下命令：

   ```
   bcdedit /export c:\bcdbackup

   attrib c:\boot\bcd -r -s -h

   ren c:\boot\bcd bcd.old

   bootrec /rebuildbcd
   ```
4. 重启计算机。

### 方法 4：替换 Bootmgr

如果方法 1、2 和 3 无法解决问题，请按照以下步骤重命名 Bootmgr 文件，并将其从驱动器 C 移动到系统保留分区。

1. 在命令提示符下，将目录更改为“系统保留”分区。
2. 若要取消隐藏文件，请运行以下命令：

   ```
   attrib -r -s -h
   ```
3. 导航到系统驱动器，然后运行以下命令：

   ```
   attrib -r -s -h
   ```
4. 若要将 bootmgr 文件重命名为 bootmgr.old，请运行以下命令：

   ```
   ren c:\bootmgr bootmgr.old
   ```
5. 导航到系统驱动器。
6. 复制 bootmgr 文件，然后将其粘贴到“系统保留”分区。
7. 重启计算机。

### 方法 5：还原系统配置单元

如果 Windows 无法将系统注册表配置单元加载到内存中，则必须还原系统配置单元。 若要执行此步骤，请使用 Windows 恢复环境或使用紧急修复磁盘 （ERD） 将文件从 C：\Windows\System32\config\RegBack 目录复制到 C：\Windows\System32\config。

如果问题仍然存在，可能需要将系统状态备份还原到备用位置，然后检索要替换的注册表配置单元。

注意

从 Windows 10 版本 1803 开始，Windows 不再自动将系统注册表备份到 RegBack 文件夹。 此更改是设计提供的，旨在帮助减少 Windows 的整体磁盘占用大小。 若要恢复注册表配置单元损坏的系统，Microsoft 建议使用系统还原点。 有关详细信息，请参阅[从 Windows 10 版本 1803 开始，系统注册表不再备份到 RegBack 文件夹](../deployment/system-registry-no-backed-up-regback-folder)。

## 排查内核阶段的问题

如果系统停滞在内核阶段，你会遇到多种症状或收到多个错误消息。 这些错误消息包括但不限于以下示例：

- 在初始屏幕（Windows 徽标屏幕）后显示停止错误。
- 计算机显示特定的错误代码，例如 `0x00000C2`， `0x0000007B`或 `inaccessible boot device`。 有关排查这些错误的详细信息，请参阅以下部分或文章：
  - [错误代码 INACCESSIBLE\_BOOT\_DEVICE（STOP 0x7B）](#error-code-inaccessible_boot_device-stop-0x7b)
  - [针对事件 ID 41“系统已在未先正常关机的情况下重新启动”的高级疑难解答](/zh-cn/windows/client-management/troubleshoot-event-id-41-restart)。
- 屏幕卡在“旋转轮”（滚动点）“系统忙碌”图标。
- 显示初始屏幕后出现黑屏。

若要排查这些问题，请一次尝试以下恢复选项。

### 方法 1：尝试在安全模式或上次已知良好配置中启动计算机

在“高级启动选项”屏幕上，尝试使用“安全模式”或“网络安全模式”启动计算机。 如果任一选项有效，请使用事件查看器来帮助识别和诊断启动问题的原因。 若要查看事件日志中记录的事件，请执行以下步骤：

1. 可使用以下方法之一打开事件查看器：

   - 转到 **“开始** ”菜单，然后选择 **“管理工具**>**事件查看器**”。
   - 在 Microsoft 管理控制台 (MMC) 中启动事件查看器管理单元。
2. 在控制台树中，展开事件查看器，然后选择要查看的日志。 例如，选择“系统日志”或“应用程序日志”。
3. 在详细信息窗格中，打开要查看的事件。
4. 在“编辑”菜单上，选择“复制”。 在要在其中粘贴事件的程序中打开新文档。 例如，Microsoft Word。 然后选择“粘贴”。
5. 使用向上键或向下键查看上一个或下一个事件的说明。

### 方法 2：执行“干净启动”

若要排查影响服务的问题，请使用系统配置 （`msconfig`） 工具执行干净启动。 在工具中，选择 **“选择性启动** ”，一次测试一个服务，以确定哪个服务导致问题。 如果找不到原因，请尝试包含系统服务。 但是，在大多数情况下，有问题的服务都是第三方服务。

禁用发现有故障的任何服务，并尝试通过选择“正常启动”再次启动计算机。

有关详细说明，请参阅[如何在 Windows 中执行干净启动](https://support.microsoft.com/topic/how-to-perform-a-clean-boot-in-windows-da2f9573-6eec-00ad-2f8a-a97a1807f3dd)。

如果计算机以禁用驱动程序签名模式启动，请在禁用驱动程序签名强制模式下启动计算机。 然后按照以下文章中的步骤来确定哪些驱动程序或文件需要强制实施驱动程序 [签名：排查因缺少驱动程序签名而导致的启动问题（x64）](/zh-cn/archive/blogs/askcore/troubleshooting-boot-issues-due-to-missing-driver-signature-x64)

注意

如果计算机是域控制器，请尝试目录服务还原模式 (DSRM)。

这个方法是一个重要的步骤，如果遇到“停止”错误 `0xC00002E1` 或 `0xC00002E2`.

## 常见问题和解决方案

### 错误代码 INACCESSIBLE\_BOOT\_DEVICE (STOP 0x7B)

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 如果您错误地修改注册表，可能会出现严重问题。 因此，请确保仔细执行这些步骤。 出于防范目的，请在修改之前备份注册表，以便在出现问题时还原注册表。 有关如何备份和恢复注册表的更多信息，请参见[如何在 Windows 中备份和恢复注册表](https://support.microsoft.com/help/322756)。

要对此停止错误进行疑难解答，请按照以下步骤筛选驱动程序：

1. 通过将系统的 ISO 磁盘放入磁盘驱动器，转到 Windows 恢复环境 (WinRE)。 ISO 应具有相同版本的 Windows 或更高版本。
2. 打开注册表。
3. 加载系统配置单元并将其命名为 *test*。
4. 在以下注册表子项下，检查非 Microsoft 驱动程序的下级筛选器项和上级筛选器项：

   `HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Control\Class`
5. 对于找到的每个第三方驱动程序，选择上级或下级筛选器，然后删除值数据。
6. 在整个注册表中搜索类似项。 根据需要处理，然后卸载注册表配置单元。
7. 在正常模式下重启服务器。

有关更多疑难解答步骤，请参阅[停止错误 7B 或 Inaccessible\_Boot\_Device 的高级疑难解答](stop-error-7b-or-inaccessible-boot-device-troubleshooting)。

#### 安装 Windows 更新后出现的问题

为了解决安装 Windows 更新后出现的问题，请按照以下步骤检查正在等待的更新：

1. 在 WinRE 中打开命令提示符窗口。
2. 运行下面的命令：

   ```
   DISM /image:C:\ /get-packages
   ```
3. 如果有任何挂起的更新，请运行以下命令将其卸载：

   ```
   DISM /image:C:\ /remove-package /packagename: name of the package

   DISM /Image:C:\ /Cleanup-Image /RevertPendingActions
   ```
4. 尝试启动计算机。

如果计算机未启动，请执行以下步骤：

1. 在 WinRE 中打开命令提示符窗口，并启动文本编辑器，例如记事本。
2. 进入系统盘，并搜索 windows\winsxs\pending.xml。
3. 如果找到 pending.xml 文件，请将该文件重命名为 .old pending.xml。
4. 打开注册表，然后在HKEY\_LOCAL\_MACHINE中加载组件配置单元作为 *test*。
5. 突出显示已加载的测试配置单元，然后搜索 `pendingxmlidentifier` 该值。
6. 如果存在该值 `pendingxmlidentifier` ，请将其删除。
7. 卸载测试配置单元。
8. 加载系统配置单元，然后将其命名*测试*。
9. 导航到以下子项：

   `HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\TrustedInstaller`
10. 将“开始”值从 **1** 更改为 **4**。
11. 卸载配置单元。
12. 尝试启动计算机。

如果在启动过程中发生“停止”错误，或者“停止”错误继续发生，则可以捕获内存转储。 良好的内存转储有助于确定停止错误的根本原因。 有关详细信息，请参阅[生成内核或完整的故障转储](generate-a-kernel-or-complete-crash-dump)。

有关 Windows 10 或 Windows Server 2016 中的页面文件问题的详细信息，请参阅 [页面文件简介](introduction-to-the-page-file)。

有关停止错误的详细信息，请参阅[停止错误或蓝屏错误问题的高级疑难解答](stop-error-or-blue-screen-error-troubleshooting)。

有时转储文件显示与驱动程序相关的错误。 例如，windows\system32\drivers\stcvsm.sys 缺失或损坏。 在此实例中，请遵循以下准则：

- 检查驱动程序提供的功能。 如果驱动程序是第三方启动驱动程序，请确保了解它的用途。
- 如果驱动程序不重要且没有依赖项，请加载系统配置单元，然后禁用该驱动程序。
- 如果停止错误指示系统文件损坏，请在脱机模式下运行系统文件检查器。

  - 若要执行此操作，请打开 WinRE，打开命令提示符，然后运行以下命令：

    ```
    SFC /Scannow /OffBootDir=C:\ /OffWinDir=C:\Windows
    ```

    有关详细信息，请参阅[使用系统文件检查器 (SFC) 修复问题](/zh-cn/archive/blogs/askcore/using-system-file-checker-sfc-to-fix-issues)。
  - 如果磁盘损坏，请运行检查磁盘命令：

    ```
    chkdsk /f /r
    ```
- 如果停止错误指示一般注册表损坏，或者你认为安装了新的驱动程序或服务，请执行以下步骤：

  1. 启动 WinRE，然后打开命令提示符窗口。
  2. 启动一个文本编辑器（例如记事本）。
  3. 导航到 C：\Windows\System32\Config\。
  4. 通过向名称追加 `.old` 来重命名所有五个配置单元。
  5. 从 RegBack 文件夹中复制所有配置单元，将其粘贴到 Config 文件夹中，然后尝试以正常模式启动计算机。

注意

从 Windows 10 版本 1803 开始，Windows 不再自动将系统注册表备份到 RegBack 文件夹。 此更改是设计提供的，旨在帮助减少 Windows 的整体磁盘占用大小。 若要恢复注册表配置单元损坏的系统，微软建议使用系统还原点。 有关详细信息，请参阅[从 Windows 10 版本 1803 开始，系统注册表不再备份到 RegBack 文件夹](../deployment/system-registry-no-backed-up-regback-folder)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/windows-boot-issues-troubleshooting)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
