# 启用 Hyper-V 时 Windows 任务管理器显示不正确的 CPU 速度

本文提供了一种解决方法，用于在启用 Hyper-V 时 Windows 任务管理器显示不正确的 CPU 速度的问题。

*适用于：* Windows 10 - 所有版本，Window Server 2012 R2  
*原始 KB 数：* 3003081

## 现象

如果在本文开头列出的任何产品中启用了 Hyper-V 角色， **则任务管理器中显示的 CPU 频率** 速度值不是当前速度，如预期所示。 如果未启用 Hyper-V 角色，任务管理器将正确显示此值的当前速度。

## 解决方法

若要解决此问题，请使用内置性能监视器工具（perfmon.exe），并添加“\Hyper-V 虚拟机监控程序逻辑处理器\频率”性能计数器。

## Status

这是本文开头列出的产品版本中的已知问题。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/task-manager-shows-incorrect-cpu-speed)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
