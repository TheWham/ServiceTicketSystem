# 停止错误 7B 或 Inaccessible\_Boot\_Device 的高级问题排查

本文提供用于排查“停止错误 7B：Inaccessible\_Boot\_Device”的步骤。 在对计算机进行某些更改或在计算机上部署 Windows 之后立即发生此错误。

*Applies to:* Windows 10

## Inaccessible\_Boot\_Device停止错误的原因

以下任一因素都可能导致停止错误：

- 与存储堆栈相关的缺失、损坏或行为不当的筛选器驱动程序
- 文件系统损坏
- 对 BIOS 中的存储控制器模式或设置的更改
- 使用与安装 Windows 时使用的存储控制器不同的存储控制器
- 将硬盘移动到具有不同控制器的其他计算机
- 有故障的主板或存储控制器，或硬件故障
- 在异常情况下，TrustedInstaller 服务提交新安装的更新失败是因为基于组件的存储损坏
- Corrupted files in the Boot partition (for example, corruption in the volume that's labeled **SYSTEM** when you run the `diskpart`>`list vol` command)
- 如果在启动分区的条目之前有一个空的 GPT 条目

## 排查Inaccessible\_Boot\_Device停止错误

按照以下步骤在 Windows 恢复模式（WinRE）[中](/zh-cn/windows-hardware/manufacture/desktop/windows-recovery-environment--windows-re--technical-reference#span-identrypointsintowinrespanspan-identrypointsintowinrespanspan-identrypointsintowinrespanentry-points-into-winre)启动计算机。

1. 使用 [已安装版本的 Windows](https://support.microsoft.com/help/15088) 安装介质启动系统。
2. On the **Install Windows** screen, select **Next**>**Repair your computer**.
3. 在**“系统恢复选项**”屏幕上，选择“**下一步>命令提示符”。**

### 验证启动磁盘是否已连接且可访问

#### Step 1

在 WinRE 命令提示符处，运行 `diskpart`，然后运行 `list disk`。

应显示附加到计算机的物理磁盘的列表，如下所示：

```
  Disk ###  Status         Size     Free     Dyn  Gpt

  --------  -------------  -------  -------  ---  ---

  Disk 0    Online         **size*  GB      0 B        *
```

如果计算机使用统一可扩展固件接口（UEFI）启动接口，则`*`列中将有一个星号（`GPT`）。

如果计算机使用基本输入/输出系统（BIOS）接口，则列中不会有星号 `Dyn` 。

#### Step 2

`list disk`如果命令正确列出 OS 磁盘，请在其中`list vol``diskpart`运行该命令。

`list vol` 生成类似于以下显示的输出：

```
  Volume ###  Ltr  Label        Fs     Type        Size     Status     Info

  ----------  ---  -----------  -----  ----------  -------  ---------  --------

  Volume 0         Windows RE   NTFS   Partition    499 MB  Healthy

  Volume 1     C   OSDisk       NTFS   Partition    222 GB  Healthy    Boot

  Volume 2         SYSTEM       FAT32  Partition    499 MB  Healthy    System
```

Note

如果包含 OS 的磁盘未在输出中列出，则必须与 OEM 或虚拟化制造商联系。

### 验证启动配置数据库的完整性

检查启动配置数据库（BCD）是否具有所有正确的条目。 若要执行此步骤，请在 WinRE 命令提示符下运行 `bcdedit` 。

验证 BCD 条目：

1. **检查具有 {bootmgr} **标识符的** Windows 启动管理器**部分。 Make sure that the **device** and **path** entries point to the correct device and boot loader file.

   如果计算机基于 UEFI，则下面是示例输出：

   ```
   device                  partition=\Device\HarddiskVolume2
   path                    \EFI\Microsoft\Boot\bootmgfw.efi
   ```

   如果计算机基于 BIOS，下面是示例输出：

   ```
   Device                partition=C:
   ```

   Note

   此输出可能不包含路径。
2. 在**具有 {default} **标识符的** Windows 启动加载程序**中**，确保设备**、**路径**、**osdevice** 和 **systemroot** 指向正确的设备或分区、winload 文件、OS 分区或设备以及 OS 文件夹。

   Note

   If the computer is UEFI-based, the file path value that's specified in the **path** parameter of **{bootmgr}** and **{default}** contains an **.efi** extension.

   ![bcdedit 输出的屏幕截图，其中包含 Windows 启动加载程序的详细信息。](media/stop-error-7b-or-inaccessible-boot-device-troubleshooting/windows-boot-loader.png)

如果任何信息错误或缺失，建议创建 BCD 存储的备份。 为此，请运行 `bcdedit /export C:\temp\bcdbackup`。 This command creates a backup in *C:\temp\* that's named **bcdbackup**. 若要还原备份，请运行 `bcdedit /import C:\temp\bcdbackup`。 This command overwrites all BCD settings by using the settings in **bcdbackup**.

备份完成后，运行以下命令以进行更改：

```
bcdedit /set *{identifier}* option value
```

例如，如果 {default} 下的设备出错或缺失，请运行以下命令来设置它： `bcdedit /set {default} device partition=C:`

如果要完全重新创建 BCD，或者收到一条消息，指出“**无法打开启动配置数据存储”。系统找不到指定的文件，** “运行 `bootrec /rebuildbcd`。

If the BCD has the correct entries, check whether the **winload** and **bootmgr** entries exist in the correct location, which is in the specified path in the **bcdedit** command. By default, **bootmgr** in the BIOS partition is in the root of the **SYSTEM** partition. 若要查看该文件，请运行 `Attrib -s -h -r`。

如果文件缺失，并且想要重新生成启动文件，请执行以下步骤：

1. Copy all the contents under the **SYSTEM** partition to another location. Alternatively, you can use the command prompt to navigate to the OS drive, create a new folder, and then copy all the files and folders from the **SYSTEM** volume, like shown here:

   ```
   D:\> Mkdir  BootBackup
   R:\> Copy *.* D:\BootBackup
   ```
2. 如果你使用的是 Windows 10，或者在 Windows 预安装环境命令提示符处使用 Windows 10 ISO 进行故障排除，则可以使用 `bcdboot` 命令重新创建启动文件，如下所示：

   ```
   Bcdboot <**OSDrive* >:\windows /s <**SYSTEMdrive* >: /f ALL
   ```

   例如，如果为字母 R 分配 `<System Drive>` 了 （WinRE 驱动器），并且 `<OSdrive>` 是字母 D，我们将使用以下命令：

   ```
   Bcdboot D:\windows /s R: /f ALL
   ```

   Note

   The **ALL** part of the `bcdboot` command writes all the boot files (both UEFI and BIOS) to their respective locations.

If you don't have a Windows 10 ISO, format the partition and copy **bootmgr** from another working computer that has a similar Windows build. 若要执行格式设置和复制，请执行以下步骤：

1. Start **Notepad**.
2. Press Ctrl+O.
3. 导航到系统分区（在此示例中为 R）。
4. 右键单击分区，然后设置其格式。

### 如果在安装Windows 更新后出现此问题，请进行故障排除

运行以下命令来验证 Windows 更新安装和日期：

```
Dism /Image:<Specify the OS drive>: /Get-packages
```

After you run this command, you'll see the **Install pending** and **Uninstall Pending** packages:

![Dism 输出挂起更新的屏幕截图。](media/stop-error-7b-or-inaccessible-boot-device-troubleshooting/pending-update.png)

1. 运行 `dism /Image:C:\ /Cleanup-Image /RevertPendingActions` 命令。 将 C：替换为计算机的系统分区。

   ![Dism 输出还原挂起的屏幕截图。](media/stop-error-7b-or-inaccessible-boot-device-troubleshooting/revert-pending.png)
2. Navigate to *OSdriveLetter:\Windows\WinSxS*, and then check whether the *pending.xml* file exists. If it does, rename it to *pending.xml.old*.
3. To revert the registry changes, type *regedit* at the command prompt to open **Registry Editor**.
4. Select **HKEY\_LOCAL\_MACHINE**, and then go to **File**>**Load Hive**.
5. Navigate to *OSdriveLetter:\Windows\System32\config*, select the file that's named *COMPONENT* (with no extension), and then select **Open**. When you're prompted, enter the name *OfflineComponentHive* for the new hive.

   ![注册表编辑器的屏幕截图，其中打开了“加载 Hive”窗口。](media/stop-error-7b-or-inaccessible-boot-device-troubleshooting/load-hive.png)
6. Expand `HKEY_LOCAL_MACHINE\OfflineComponentHive`, and check whether the **PendingXmlIdentifier** key exists. Create a backup of the **OfflineComponentHive** key, and then delete the **PendingXmlIdentifier** key.
7. 卸载配置单元。 To do this unloading, highlight **OfflineComponentHive**, and then select **File**>**Unload hive**.

   ![选择了“脱机”的注册表编辑器的屏幕截图。](media/stop-error-7b-or-inaccessible-boot-device-troubleshooting/unload-hive-offlinehive.png)

   ![注册表编辑器的屏幕截图，其中选择了“卸载 Hive”选项。](media/stop-error-7b-or-inaccessible-boot-device-troubleshooting/unload-hive-selected.png)
8. Select **HKEY\_LOCAL\_MACHINE**, go to **File**>**Load Hive**, navigate to *OSdriveLetter:\Windows\System32\config*, select the file that's named **SYSTEM** (with no extension), and then select **Open**. When you're prompted, enter the name **OfflineSystemHive** for the new hive.
9. Expand **HKEY\_LOCAL\_MACHINE\OfflineSystemHive**, and then select the **Select** key. Check the data for the **Default** value.
10. If the data in `HKEY_LOCAL_MACHINE\OfflineSystemHive\Select\Default` is **1**, expand `HKEY_LOCAL_MACHINE\OfflineHive\ControlSet001`. If it's **2**, expand `HKEY_LOCAL_MACHINE\OfflineHive\ControlSet002`, and so on.
11. 展开 `Control\Session Manager`。 Check whether the **PendingFileRenameOperations** key exists. If it does, back up the **SessionManager** key, and then delete the **PendingFileRenameOperations** key.

### 验证启动关键驱动程序和服务

#### Check services

1. 按照“在安装Windows 更新后出现此问题时进行故障排除”部分中的步骤 1-10。 （步骤 11 不适用于此过程。
2. Expand **Services**.
3. Make sure that the following registry keys exist under **Services**:

   - ACPI
   - DISK
   - VOLMGR
   - PARTMGR
   - VOLSNAP
   - VOLUME

   If these keys exist, check each one to make sure that it has a value that's named **Start**, and that it's set to **0**. If it's not, set the value to **0**.

   If any of these keys don't exist, you can try to replace the current registry hive by using the hive from **RegBack**. 若要执行此步骤，请运行以下命令：

   ```
   cd OSdrive:\Windows\System32\config
   ren SYSTEM SYSTEM.old
   copy OSdrive:\Windows\System32\config\RegBack\SYSTEM OSdrive:\Windows\System32\config\
   ```

#### 检查上下筛选器驱动程序

检查计算机上是否有任何非Microsoft上下筛选器驱动程序，以及它们是否存在于另一台类似的工作计算机上。 如果它们确实存在，请删除上下筛选器驱动程序：

1. 展开 `HKEY_LOCAL_MACHINE\OfflineHive\ControlSet001\Control`。
2. Look for any **UpperFilters** or **LowerFilters** entries.

   Note

   这些筛选器主要与存储相关。 After you expand the **Control** key in the registry, you can search for **UpperFilters** and **LowerFilters**.

   你可能会在以下一些注册表项中找到这些筛选器驱动程序。 These entries are under **ControlSet** and are designated as **Default**:

   - `\Control\Class\{4D36E96A-E325-11CE-BFC1-08002BE10318}`
   - `\Control\Class\{4D36E967-E325-11CE-BFC1-08002BE10318}`
   - `\Control\Class\{4D36E97B-E325-11CE-BFC1-08002BE10318}`
   - `\Control\Class\{71A27CDD-812A-11D0-BEC7-08002BE2092F}`

   ![注册表编辑器的屏幕截图，其中显示了 ControlSet 下的条目。](media/stop-error-7b-or-inaccessible-boot-device-troubleshooting/controlset-entries.png)

   If an **UpperFilters** or **LowerFilters** entry is non-standard (for example, it's not a Windows default filter driver, such as PartMgr), remove the entry. 若要删除它，请在右窗格中双击它，然后仅删除该值。

   Note

   可能有多个条目。

   These entries might affect us because there might be an entry in the **Services** branch that has a START type set to 0 or 1, which means that it's loaded at the Boot or Automatic part of the boot process. 此外，引用的文件丢失或损坏，或者其命名方式可能与条目中列出的文件不同。

   Note

   If there's a service that's set to **0** or **1** that corresponds to an **UpperFilters** or **LowerFilters** entry, setting the service to disabled in the **Services** registry (as discussed in steps 2 and 3 of the Check services section) without removing the **Filter Driver** entry causes the computer to crash and generate a 0x7b Stop error.

### 运行 SFC 和 Chkdsk

如果计算机仍未启动，可以尝试 `chkdisk` 在系统驱动器上运行进程，然后运行系统文件检查器。 通过在 WinRE 命令提示符处运行以下命令来执行这些步骤：

- ```
  chkdsk /f /r OsDrive:
  ```

  ![chkdsk 命令输出的屏幕截图。](media/stop-error-7b-or-inaccessible-boot-device-troubleshooting/check-disk.png)
- ```
  sfc /scannow /offbootdir=OsDrive:\ /offwindir=OsDrive:\Windows
  ```

  ![SFC 扫描命令输出的屏幕截图。](media/stop-error-7b-or-inaccessible-boot-device-troubleshooting/sfc-scannow.png)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/stop-error-7b-or-inaccessible-boot-device-troubleshooting)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
