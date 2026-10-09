# 使用 LiveRE 排查 Windows 启动问题

LiveRE 工具创建一个图像，该映像可用于通过 USB 连接启动计算机。 此工具有助于排查“无启动”问题。 它还可用于通过跳转服务器为支持专业人员提供对非启动计算机的远程访问。

注意

本文适用于支持代理和 IT 专业人员。

## LiveRE 到 WinRE 比较

下面是 Live RE 与 Windows ISO 附带的现有 Windows 恢复环境的比较。

| 功能 | WinRE/WinPE | iDRAC/伊洛伊洛 | 实时操作系统 （OS） |
| --- | --- | --- | --- |
| 可用性 | 使用 DVD | 特殊硬件 | 闪存驱动器 |
| 远程访问 | 否 | 是 | 是 |
| DISM | 是 | 通过 WinRE | 是，能够从 Internet 下载缺少的有效负载 |
| DiskPart | 是 | 通过 WinRE | 否，但 PowerShell 等效工作 |
| BitLocker | 是 | 通过 WinRE | 是 |
| 复制/粘贴以允许减少研究和记录记录 | 否 | No | 是 |
| 调用 PowerShell 脚本 | 否 | No | 是 |
| 对卷影副本的访问 | 否 | No | 是 |

## 系统要求

- 处理器：1.4Ghz 64 位处理器
- RAM：512 MB
- 磁盘空间：32 GB
- 网络：千兆位（10/100/1000baseT）以太网适配器（1 Gbps 连接理想）
- 光学存储：DVD 驱动器（如果从 DVD 媒体安装 OS）
- USB 3.0 闪存驱动器，8 GB 或更高版本
- 视频：超级 VGA （1024x768） 或更高版本 （可选）
- 输入设备：键盘和鼠标（可选）
- Internet：宽带访问（可选）

## 设置 U 盘

1. [下载 LiveRE 映像](https://download.microsoft.com/download/7/e/b/7ebcc4f5-e67f-45b1-b00f-48870d9350a5/LiveRE.wim)。
2. 连接 USB 闪存驱动器。
3. 检查是否为 BIOS 启动或 UEFI 启动设置了非启动计算机。 相应地设置 USB 驱动器的格式：

   - 对于 UEFI：

     ```
     Diskpart
     List disk
     Sel disk <the number of the flash drive>
     Clean
     Convert gpt
     Create part pri
     Exit
     ```

     格式化 FAT32 文件系统的分区。
   - 对于 MBR 启动：

     ```
     Diskpart
     List disk
     Sel disk <the number of the flash drive>
     Clean
     Convert mbr
     Create part pri
     List part
     Sel part 1
     active
     Exit
     ```

     格式化 NTFS 文件系统的分区。
4. 运行以下命令：

   ```
   dism /Apply-Image /ImageFile:<complete path of the LiveOS.wim> /Index:1 /ApplyDir:<flash drive letter>:\
   <flash drive letter>:\Windows\System32\bcdboot <flash drive letter>:\Windows /s <flash drive letter>: /f ALL
   ```

USB 闪存驱动器准备就绪后，从闪存驱动器启动受影响的服务器。

## 创建用于远程访问的用户帐户

以下步骤可帮助创建用户以通过跳转服务器启用远程访问：

1. 使用 USB 闪存驱动器启动问题计算机。 接受 EULA 以转到帮助控制台。
2. 按 Enter 访问 PowerShell。
3. 运行以下 cmdlet：

   ```
   $Password = Read-Host -AsSecureString

   New-LocalUser "user_name" -Password $Password
   Add-LocalGroupMember -Group "Administrators" -Member "user_name"
   ```

   注意

   在第一个 cmdlet 之后输入密码。

计算机现已设置为通过跳转服务器进行远程访问。 以下屏幕截图显示了一个示例 cmdlet。

![在 LiveRE 中运行“新用户帐户”cmdlet。](media/live-re-troubleshoot-windows-boot/live-re-input-add-user.png)

## 从跳转服务器进行连接

1. 从 LiveRE 屏幕获取 IP 地址。

   ![获取 IP 地址。](media/live-re-troubleshoot-windows-boot/get-ip-address-from-live-re.png)
2. 在与非启动计算机相同的网络中的工作计算机上，打开 PowerShell ISE 并运行以下脚本：

   ```
   $ip = "172.25.80.68"
   Set-Item WSMan:\localhost\Client\TrustedHosts $ip
   $user = "$ip\user_name"  
   Enter-PSSession -ComputerName $ip -Credential $user
   ```
3. 出现提示时，输入密码。
4. 你将通过 WinRM 连接到损坏的计算机。

   ![通过 WinRM 进行连接。](media/live-re-troubleshoot-windows-boot/connect-to-broken-computer-using-winrm.png)

如果在通过 WinRM 进行连接时遇到问题，请检查是否启用了 WinRM。 如果不是，请 `winrm qc` 运行命令以启用 WinRM。

如果收到重新组装以下消息的错误消息，则表示网络连接设置为 **“公共**”。

![启用 WinRM 时0x80338169错误消息。](media/live-re-troubleshoot-windows-boot/run-winrm-qc-error-0x80338169.png)

可以通过运行以下 cmdlet 来确定哪些连接设置为 **公共** ：

```
Get-NetConnectionProfile | select InterfaceAlias, NetworkCategory
```

下面是示例输出：

![Get-NetConnectionProfile cmdlet 的输出。](media/live-re-troubleshoot-windows-boot/get-netconnectionprofile-output.png)

在从客户删除权限后，可以禁用公共连接或将其更改为专用连接。 为此，请运行以下 cmdlet：

```
Set-NetConnectionProfile -interfacealias "vEthernet (Internal LAN)" -NetworkCategory Private
```

## 从 LiveRE 解锁 BitLocker 驱动器

1. 运行 `Get-Volume` 以查找驱动器号：

   ![用于查找驱动器号的 Get-Volume](media/live-re-troubleshoot-windows-boot/run-get-volume-to-find-drive-letter.png)
2. 运行下面的命令：

   ```
   Unlock-BitLocker -MountPoint <drive letter> -RecoveryPassword <recovery password>
   ```

## 磁盘配置

由于 *LiveRE 中不提供Diskpart.exe* ，因此请使用 PowerShell 来实现类似的结果。 下面是几个命令：

1. 检查磁盘： `Get-Disk`
2. 检查磁盘中的分区： `Get-Partition -DiskNumber <number>`
3. 将分区设置为活动： `Set-Partition -DiskNumber <number> -PartitionNumber <number> -IsActive $true`
4. 检查分区的属性： `Get-Partition -DiskNumber <number> -PartitionNumber <number> |fl`

有关详细信息，请参阅 [特定于 Windows 存储管理的 cmdlet](/zh-cn/powershell/module/storage/)。

## 注册表配置

没有注册表编辑器是 Live OS。 若要更改注册表，请使用 \\<IP 地址>\c$ *路径访问受影响 OS 驱动器的*共享。

从 *\windows\system32\config* 获取 Hives，对 hives 进行更改，然后继续执行后续步骤。

## 访问卷影副本

LiveRE 允许从未启动的计算机的磁盘访问卷影副本，这可用于替换以前版本的文件。

可以使用以下步骤访问文件的早期版本：

```
Get-CimInstance -ClassName Win32_ShadowCopy | select volumename,ID,InstallDate,DeviceObject
Get-Volume | select Driveletter,path to get the volume name association with Volume ID
```

注意

OS 日期和时间必须根据正确的时区进行调整才能保持准确。 LiveOS 使用协调世界时（格林威治平均时间）时区。

复制要访问的卷影副本的 DeviceObject，然后运行以下命令：

```
$sobj="<DeviceObject>" + "\"
cmd /c mklink /d c:\shadowcopy "$sobj"
```

现在可以通过浏览到 *\\IP>\<c$\shadowcopy*，从 PowerShell 访问文件的早期版本。

## 注入驱动程序

如果设置了 RAID 磁盘，则必须从 OEM 媒体安装 RAID 驱动程序，以使卷对 OS 可见。

在 LiveRE 中，可以将 RAID 驱动程序提取到 *<USB>：\CopyDriversHere* 文件夹。

然后，在 LiveRE 中启动后，按 4 键安装驱动程序。

安装驱动程序的另一种方法是执行以下操作：

1. 下载驱动程序并将其提取到 LiveRE 闪存驱动器上的文件夹。
2. 连接到受影响的 conputer 后，运行以下 cmdlet：

   ```
   pnputil /add-driver <location of raid driver.inf>

   Add-WindowsDriver -Path <flash drive letter>:\ -Driver <path of driver folder> -Recurse
   ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/live-re-troubleshoot-windows-boot)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
