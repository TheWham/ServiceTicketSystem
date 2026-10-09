# 在 Windows 中运行 64 位应用程序时，SuperFetch（SysMain）服务将 CPU 峰值 1-2 分钟

本文提供了一种解决方法，其中，当 64 位应用程序在 64 位版本的 Windows 中运行时，系统遇到 CPU 峰值 1-2 分钟的问题。

*适用于：* Windows 7 Service Pack 1  
*原始 KB 数：* 2723033

## 现象

当使用 /LARGEADDRESSAWARE：NO 选项编译的 64 位应用程序在 64 位版本的 Windows 中运行时，系统可能会遇到 1-2 分钟的 CPU 峰值，这确实会继续。 在这种情况下，任务管理器显示托管 SysMain（SuperFetch） 服务的svchost.exe进程正在使用 CPU 利用率。

## 原因

在创建进程时，Windows 为地址空间创建一个只读虚拟地址描述符（VAD）。 在扫描正在运行进程的 VAD 树时，SuperFetch 遇到 VAD，并旋转具有巨大的 VAD 大小，从而导致 CPU 峰值。

## 解决方法

若要解决此问题，请避免在编译应用程序时使用选项 /LARGEADDRESSAWARE：NO。

注意

默认情况下，64 位应用程序使用扩展地址空间（每个进程 8 TB）。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/superfetch-sysmain-service-spikes-cpu)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
