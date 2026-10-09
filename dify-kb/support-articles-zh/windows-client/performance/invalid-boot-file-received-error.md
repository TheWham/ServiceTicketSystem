# 从 WDS 启动 PXE 时收到无效启动文件错误消息

本文有助于修复使用 PXE 从 Windows 部署服务（WDS）服务器启动客户端计算机时发生的错误。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 2602043

## 症状

使用 PXE 从 WDS 服务器启动客户端计算机时，可能会遇到以下症状或错误消息之一

- 收到的启动文件无效
- PXE 客户端挂起。 在从 PXE bios 执行代码时出错，因此实际错误消息可能会有所不同。

## 原因

这种情况可能发生在以下情况下：

- 使用 DHCP 范围选项 67 指示 PXE 客户端使用 BootFileName 下载特定的启动程序。
- 混合使用基于 BIOS 的计算机和 UEFI 计算机，并尝试启动不正确的启动程序类型

## 解决方案

如果混合使用 UEFI 和旧版 BIOS 计算机，则无法使用 DHCP 范围选项将 PXE 客户端定向到 WDS 服务器上的启动程序。 必须使用 IP 帮助程序表条目。 有关配置 IP 帮助程序表条目的详细信息，请联系路由器/交换机制造商。

## 详细信息

有关适用于 UEFI 计算机的 WDS 启动程序 wdsmgfw.efi 的详细信息，请参阅 [管理网络启动程序](/zh-cn/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/cc732351%28v=ws.10%29)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/invalid-boot-file-received-error)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
