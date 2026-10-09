# 生成内核或完整的故障转储

系统崩溃（也称为“bug 检查”或“停止错误”）在 Windows 无法正常运行时发生。 此事件生成的转储文件称为系统故障转储。

在排查多个问题时，手动内核或完整的内存转储文件非常有用，因为进程在崩溃时捕获系统内存的记录。

*适用于：*Windows 10

## 设置页面文件

有关系统故障转储的页面文件大小要求，请参阅 [对系统故障转储](how-to-determine-the-appropriate-page-file-size-for-64-bit-versions-of-windows#support-for-system-crash-dumps) 的支持。

## 启用内存转储设置

必须以管理员或管理员组的成员身份登录才能完成此过程。 如果计算机已连接到网络，则网络策略设置可能会阻止你完成此过程。

若要启用内存转储设置，请执行以下步骤：

1. 在**控制面板中，选择“>”。**
2. 选择 **“高级系统设置”**，然后选择“ **高级** ”选项卡。
3. 在 **“启动和恢复** ”区域中，选择“ **设置**”。
4. 请确保在**“写入调试信息**”下选择了**内核内存转储**、**活动内存转储**、**自动内存转储**或**“完整内存转储**”。
5. 重新启动计算机。

注意

可以通过编辑 **转储文件字段来更改转储文件** 路径。 换句话说，可以将路径从 *%SystemRoot%\Memory.dmp* 更改为指向具有足够磁盘空间的本地驱动器，例如 *E：\Memory.dmp*。

### 生成内存转储的提示

当计算机崩溃并重启时，物理 RAM 的内容将写入位于操作系统所安装的分区上的分页文件。

根据安装 Windows 的硬盘的速度，转储超过 2 GB 的内存可能需要很长时间。 即使在最佳情况下，如果转储文件配置为驻留在另一个本地硬盘驱动器上，也会读取并写入硬盘上的大量数据。 此读写过程可能会导致服务器长时间中断。

注意

请谨慎使用此方法生成完整的内存转储文件。 理想情况下，仅当Microsoft 支持部门工程师显式请求时，才应执行此操作。 所有内核或完整的内存转储文件调试都应是所有标准故障排除方法完全耗尽后的最后手段。

## 手动生成内存转储文件

### 使用 NotMyFault 工具

如果在出现问题时可以登录，可以按照以下步骤使用 Microsoft Sysinternals NotMyFault 工具：

1. [下载 NotMyFault](https://download.sysinternals.com/files/NotMyFault.zip) 工具。
2. 选择“开始”，然后选择**命令提示符**。
3. 在命令行中运行以下命令：

   ```
   notmyfaultc64.exe /getdumptype = full
   notmyfaultc64.exe /crash 0x01
   ```

注意

此操作将生成内存转储文件和 D1 停止错误。

### 使用 NMI

在某些计算机上，不能使用键盘生成故障转储文件。 例如，Hewlett-Packard （HP） BladeSystem 服务器来自 Hewlett-Packard 开发公司的边栏选项卡通过基于浏览器的图形用户界面（GUI）进行管理。 键盘未附加到 HP BladeSystem 服务器。

在这些情况下，必须使用导致系统处理器上的 NMI 的非掩码中断（NMI）开关生成完整的故障转储文件或内核故障转储文件。

若要实现此过程，请执行以下步骤：

重要

请认真遵循本部分所述的步骤。 如果注册表修改不正确，可能会发生严重问题。 在修改注册表之前，请[备份注册表](https://support.microsoft.com/help/322756)，以便在出现问题时可以还原。

注意

运行 Windows 8 及更高版本的客户端或运行 Windows Server 2012 及更高版本的服务器不需要此注册表项。 在更高版本的 Windows 上设置此注册表项不起作用。

1. 在“注册表编辑器”中，找到以下注册表子项：

   `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\CrashControl`
2. 右键单击 CrashControl**，指向**“新建**”，然后选择**“DWORD 值**”。**
3. 键入 *NMICrashDump*，然后按 Enter。
4. 右键单击 **NMICrashDump**，然后选择“ **修改**”。
5. 在“值”数据框中，键入“1”，然后选择“确定”。
6. 重新启动计算机。
7. 硬件供应商（如 HP、IBM 和 Dell）可以提供自动系统恢复（ASR）功能。 应在故障排除期间禁用此功能。 例如，如果在 BIOS 中启用了 HP 和 Compaq ASR 功能，请在排除故障时禁用此功能以生成完整的Memory.dmp文件。 有关确切步骤，请联系硬件供应商。
8. 在 BIOS 中或使用集成灯出 （iLO） Web 接口启用 NMI 开关。

   注意

   有关确切步骤，请参阅 BIOS 参考手册或联系硬件供应商。
9. 使用 NMI 开关在服务器上测试此方法，以生成转储文件。 你将看到停止0x00000080硬件故障。

如果要使用串行控制台在 Azure Microsoft中运行 NMI，请参阅 [使用串行控制台进行 SysRq 和 NMI 调用](/zh-cn/azure/virtual-machines/linux/serial-console-nmi-sysrq)。

### 使用键盘

[从键盘强制系统崩溃](/zh-cn/windows-hardware/drivers/debugger/forcing-a-system-crash-from-the-keyboard)

### 使用调试器

[从调试器强制系统崩溃](/zh-cn/windows-hardware/drivers/debugger/forcing-a-system-crash-from-the-debugger)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/generate-a-kernel-or-complete-crash-dump)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
