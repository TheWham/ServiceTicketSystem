# 在 Windows 中配置系统故障和恢复选项

*适用于：*Windows 10

本文介绍如何配置 Windows 在发生系统错误时执行的操作（也称为 bug 检查、系统崩溃、严重系统错误或停止错误）。 可以配置以下操作：

- 将事件写入系统日志。
- 警报管理员（如果已设置管理警报）。
- 将系统内存放入高级用户可用于调试的文件。
- 自动重新启动计算机。

注意

必须以管理员或管理员组的成员身份登录才能完成此过程。 如果计算机已连接到网络，则网络策略设置可能会阻止你完成此过程。

## 配置系统故障和恢复选项

重要

请认真遵循本部分所述的步骤。 如果注册表修改不正确，可能会发生严重问题。 在修改注册表之前，请[备份注册表](https://support.microsoft.com/help/322756)，以便在出现问题时可以还原。

“启动和恢复**”对话框中提供了**这些选项。 还可以使用以下方法：

- 修改以下注册表子项下的值：

  `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\CrashControl`
- 若要修改本地计算机上的选项，请使用命令行实用工具（*Wmic.exe*）访问 Windows Management Instrumentation （WMI）。

按照以下步骤查看启动和恢复**中的**选项。 （每个选项也列出了注册表值和 Wmic 命令。

1. 在控制面板中，选择“**系统和安全>系统**”。
2. 选择**“高级系统设置**”，选择**“高级**”选项卡，然后在“启动和恢复**”区域中选择“**设置****”。

### 在“系统故障”下

选中希望 Windows 在发生系统错误时执行的操作的复选框。

#### 将事件写入系统日志

此选项指定在系统日志中记录事件信息。 默认情况下，此选项处于打开状态。

若要关闭此选项，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set WriteToSystemLog = False
  ```
- 将 **LogEvent** DWORD 值设置为 **0**。

#### 发送管理警报

此选项指定如果配置了管理警报，则管理员会收到系统错误的通知。 默认情况下，此选项处于打开状态。

若要关闭此选项，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set SendAdminAlert = False
  ```
- 将 **SendAlert** DWORD 值设置为 **0**。

#### 自动重启

该选项指定 Windows 自动重启计算机。 默认情况下，此选项处于打开状态。

若要关闭此选项，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set AutoReboot = False
  ```
- 将 **AutoReboot** DWORD 值设置为 **0**。

### 在“写入调试信息”下

如果计算机意外停止，请选择希望 Windows 在内存转储文件中记录的下列信息类型之一：

#### (none)

此选项不会记录内存转储文件中的任何信息。

若要指定你不希望 Windows 在内存转储文件中记录信息，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set DebugInfoType = 0
  ```
- 将 **CrashDumpEnabled** DWORD 值设置为 **0**。

#### 小规模内存转储

该选项记录最少的信息量，以帮助识别问题。 此选项需要在计算机的启动卷上至少 2 兆字节（MB）的分页文件，并指定每次系统意外停止时，Windows 都会创建新文件。 这些文件的历史记录存储在小转储目录（*%SystemRoot%\Minidump*）下列出的文件夹中。 在 Windows XP 和 Windows Server 2003 中，小型内存转储文件与Windows 错误报告功能一起使用。

若要指定要使用小型内存转储文件，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set DebugInfoType = 3
  ```
- 将 **CrashDumpEnabled** DWORD 值设置为 **3**。

若要指定要使用文件夹作为小型转储目录，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set MiniDumpDirectory = <folderpath>
  ```
- 将 **MinidumpDir** 可扩展字符串值设置为 <folderpath>。

#### 内核内存转储

选项仅记录内核内存。 此选项比小型内存转储文件存储更多信息，但完成所需的时间比完整的内存转储文件要少。 默认情况下，该文件存储在 %SystemRoot%\Memory.dmp中，如果 **选中“覆盖任何现有文件”复选框，则会覆盖任何以前的内核或完整的内存转储文件** 。 如果设置此选项，则必须在启动卷上具有足够大的分页文件。 所需大小取决于计算机中的 RAM 量。 但是，32 位系统上内核内存转储的最大可用空间量为 2 GB 和 16 MB。 在 64 位系统上，内核内存转储必须可用的最大空间量是 RAM 大小加上 128 MB。 下表提供了分页文件大小的准则：

| RAM 大小 | 分页文件不应小于 |
| --- | --- |
| 256 MB–1,373 MB | RAM 大小的 1.5 倍 |
| 1,374 MB 或更高版本 | 32 位系统：2 GB 加上 16 MB   64 位系统：RAM 大小加上 128 MB |

若要指定要使用内核内存转储文件，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set DebugInfoType = 2
  ```
- 将 **CrashDumpEnabled** DWORD 值设置为 **2**。

若要指定要使用文件作为内存转储文件，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set DebugFilePath = <filepath>
  ```
- 将 **DumpFile** 可扩展字符串值设置为 <filepath>。

若要指定不想覆盖任何以前的内核或完整的内存转储文件，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set OverwriteExistingDebugFile = 0
  ```
- 将 **Overwrite** DWORD 值设置为 **0**。

#### 完整内存转储

此选项记录计算机意外停止时系统内存的内容。 此选项在 RAM 为 2 或更多 GB 的计算机上不可用。 如果选择此选项，则必须在启动卷上有一个分页文件，该文件足以容纳所有物理 RAM 加上 1 MB。 默认情况下，该文件按 %SystemRoot%\Memory.dmp *中指定的方式*存储。

完整内存转储文件需要额外的兆字节，因为 Windows 除了转储内存内容外，还会写入标头。 标头包含故障转储签名，并指定某些内核变量的值。 标头信息不需要全兆字节的空间，但 Windows 会以兆字节为单位调整分页文件的大小。

若要指定要使用完整的内存转储文件，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set DebugInfoType = 1
  ```
- 将 **CrashDumpEnabled** DWORD 值设置为 **1**。

若要指定要使用文件作为内存转储文件，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set DebugFilePath = <filepath>
  ```
- 将 DumpFile 可扩展字符串值设置为 <filepath>。

若要指定不想覆盖任何以前的内核或完整的内存转储文件，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set OverwriteExistingDebugFile = 0
  ```
- 将 **Overwrite** DWORD 值设置为 **0**。

#### 自动内存转储

这是默认选项。 自动内存转储包含与内核内存转储相同的信息。 这两者之间的区别在于 Windows 设置系统分页文件的大小。 如果系统分页文件大小设置为 **系统托管大小**，并且内核模式故障转储设置为**自动内存转储**，则 Windows 可以将分页文件的大小设置为小于 RAM 的大小。 在这种情况下，Windows 会将分页文件的大小设置地足够大，以确保大部分时间都可以捕获内核内存转储。

如果计算机崩溃并且分页文件不够大，无法捕获内核内存转储，Windows 会将分页文件的大小增加到至少 RAM 的大小。 有关详细信息，请参阅 [自动内存转储](/zh-cn/windows-hardware/drivers/debugger/automatic-memory-dump)。

若要指定要使用自动内存转储文件，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set DebugInfoType = 7
  ```
- 将 **CrashDumpEnabled** DWORD 值设置为 **7**。

若要指定要使用文件作为内存转储文件，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set DebugFilePath = <filepath>
  ```
- 将 **DumpFile** 可扩展字符串值设置为 <filepath>。

若要指定不想覆盖任何以前的内核或完整的内存转储文件，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set OverwriteExistingDebugFile = 0
  ```
- 将 **Overwrite** DWORD 值设置为 **0**。

#### 活动内存转储

活动内存转储与完全内存转储类似，但它会过滤掉可能与主机故障诊断无关的页面。 由于此筛选，它通常比完整内存转储小得多。

此转储文件包括分配给用户模式应用程序的任何内存。 它还包括分配给 Windows 内核和硬件抽象层的内存，以及分配给内核模式驱动程序和其他内核模式程序的内存。 转储包括映射到内核或用户空间的活动页，这些页面可用于调试，以及所选的 Pagefile 支持的转换、待机和修改的页面，例如使用 VirtualAlloc 或页文件支持的分区分配的内存。 活动转储不包括免费列表和零列表、文件缓存、来宾 VM 页和在调试过程中可能不可用的各种其他类型的内存。 有关详细信息，请参阅 [活动内存转储](/zh-cn/windows-hardware/drivers/debugger/active-memory-dump)。

若要指定要使用活动内存转储文件，请修改注册表值：

- 将 **CrashDumpEnabled** DWORD 值设置为 **1**。
- 将 **FilterPages** DWORD 值设置为 **1**。

若要指定要使用文件作为内存转储文件，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set DebugFilePath = <filepath>
  ```
- 将 DumpFile 可扩展字符串值设置为 <filepath>。

若要指定不想覆盖任何以前的内核或完整的内存转储文件，请运行以下命令或修改注册表值：

- ```
  wmic recoveros set OverwriteExistingDebugFile = 0
  ```
- 将 **Overwrite** DWORD 值设置为 **0**。

注意

如果联系Microsoft 支持部门有关“停止”错误的信息，系统可能会要求你输入由“写入调试信息”选项生成的内存转储文件。

若要查看本地计算机的系统故障和恢复设置，请在命令提示符处键入 `wmic recoveros` ，然后按 Enter。 若要查看本地网络上远程计算机的系统故障和恢复设置，请在命令提示符处键入 `wmic /node:<computer_name> recoveros` ，然后按 Enter。

注意

若要成功使用这些 *Wmic.exe* 命令行示例，必须使用计算机上具有管理权限的用户帐户登录。 如果未使用计算机上具有管理权限的用户帐户登录，请使用 `/user:user_name` 和 `/password:password` 切换。

### 提示

- 若要利用转储文件功能，分页文件必须位于启动卷上。 如果已将分页文件移动到另一个卷，则必须将其移回启动卷，然后才能使用此功能。
- 如果设置了“内核内存转储”或“完整内存转储”选项，并且选中“ **覆盖任何现有文件** ”复选框，则 Windows 始终会写入同一文件名。 若要保存单个转储文件，请单击清除 **“覆盖任何现有文件** ”复选框，然后在每次停止错误后更改文件名。
- 如果单击以清除将 **事件写入系统日志** 并 **发送管理警报** 复选框，则可以节省一些内存。 保存的内存取决于计算机，但这些功能通常需要大约 60-70 KB。

## 参考

[内核模式转储文件的种类](/zh-cn/windows-hardware/drivers/debugger/varieties-of-kernel-mode-dump-files)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/configure-system-failure-and-recovery-options)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
