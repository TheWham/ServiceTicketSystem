# 更改系统 Bios 中的 ATA 驱动器设置会导致重新启动循环

本文提供了通过更改 ATA 驱动器设置导致的重新启动循环问题的解决方案。

*适用于：* Windows 8  
*原始 KB 数：* 2751461

## 现象

假设出现了下面这种情景：

- 驱动器的 BIOS 设置设置为 ATA 模式。
- 安装或将系统升级到 Windows 8。
- 启动到 BIOS，并将 ATA 设置从 ATA 模式更改为 AHCI 模式，按 Enter 接受更改。
- 单击“是”，查看有关嵌入式 ATA 控制器上检测到的模式更改的警告。
- 请重新启动计算机并正常启动。
  在此方案中，在 Windows 尝试启动时系统启动期间，你将收到有关系统故障的错误。 系统将停滞在重新启动循环中。

## 原因

这是因为 Windows 8 PnP 中默认未安装启动驱动程序的更改。

## 解决方法

若要更正此问题，请演练以下步骤：

1. 关闭或重启计算机并输入系统 BIOS。
2. 将 ATA 驱动器设置更改回 ATA 模式，按 Enter 接受更改并重新启动计算机。
3. 单击“是”，查看有关嵌入式 ATA 控制器上检测到的模式更改的警告。
4. 系统将正常启动到新式应用“开始”菜单。

   注意

   请确保知道本地管理员帐户和密码，并且能够在继续操作之前成功启动。
5. 打开提升的命令提示符并运行以下命令以启用 SafeMode 启动：bcdedit /set {current} safeboot minimal
6. 重新启动计算机并启动到系统 BIOS。
7. 将 ATA 驱动器设置从 ATA 模式更改为 AHCI 模式，按 Enter 接受更改。
8. 单击“是”，查看有关嵌入式 ATA 控制器上检测到的模式更改的警告。
9. 系统将正常启动到 SafeMode 中的新式应用启动菜单。
10. 打开提升的命令提示符并运行以下命令以删除 SafeMode 启动选项：

    ```
    bcdedit /deletevalue {current} safeboot
    ```
11. 重启计算机并正常启动，系统将成功启动到新式应用启动菜单。

## 详细信息

有关类似方案中 Windows 7 的其他信息，请参阅以下 KB。

在更改启动驱动器的 SATA 模式后启动 Windows 7 或基于 Windows Vista 的计算机时出现错误消息：“停止0x0000007B INACCESSABLE\_BOOT\_DEVICE”[https://support.microsoft.com/kb/922976](https://support.microsoft.com/help/922976)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/changing-bios-ata-drive-causes-reboot-loop)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
