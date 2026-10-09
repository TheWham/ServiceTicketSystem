# 更新内置 Broadcom 网络适配器驱动程序时发生停止错误

此问题会影响满足以下条件的计算机：

- 操作系统是 Windows Server 2019 版本 1809。
- 网络适配器是 Broadcom NX1 千兆位以太网网络适配器。
- 逻辑处理器的数量很大（例如，具有 38 个以上的逻辑处理器的计算机）。

在此类计算机上，将现成的 Broadcom 网络适配器驱动程序更新到更高版本或安装 Intel 芯片集驱动程序时，计算机遇到“停止”错误（也称为蓝屏错误或 bug 检查错误）。

## 原因

Windows Server 2019 版本 1809 的操作系统媒体包含 Broadcom NIC 驱动程序的版本 17.2。 将此驱动程序升级到更高版本时，卸载版本 17.2 驱动程序的过程将生成错误。 这是一个已知问题。

此问题已在 Windows Server 2019 版本 1903 中解决。 操作系统媒体使用较新版本的 Broadcom 网络适配器驱动程序。

## 解决方法

若要更新受影响计算机上的 Broadcom 网络适配器驱动程序，请执行以下步骤：

注意

此过程介绍如何使用设备管理器禁用和重新启用 Broadcom 网络适配器。 或者，可以使用计算机 BIOS 禁用并重新启用适配器。 有关具体说明，请参阅 OEM BIOS 配置指南。

1. 将驱动程序更新下载到受影响的计算机。
2. 打开设备管理器，然后选择 Broadcom 网络适配器。
3. 右键单击适配器，然后选择“ **禁用设备**”。
4. 再次右键单击适配器，然后选择“**更新驱动程序>浏览我的计算机以获取驱动程序软件”。**
5. 选择下载的更新，然后启动更新。
6. 更新完成后，右键单击适配器，然后选择“ **启用设备**”。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/stop-error-broadcom-network-driver-update)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
