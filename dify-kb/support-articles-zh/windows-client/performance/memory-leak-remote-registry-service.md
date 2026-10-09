# 远程注册表服务中的内存泄漏导致 Windows 挂起

本文提供了远程注册表服务中导致 Windows 挂起的内存泄漏问题的解决方法。

注意

此问题已在 Windows 10 中修复。

*适用于：*受支持的 Windows Server 和 Windows 客户端版本  
*原始 KB 数：* 3105719

## 现象

在基于 Windows 的计算机上，你注意到消耗的系统内存和分页池内存超出预期。 此内存泄漏发生在系统运行时间大约 10 分钟后，最终导致系统挂起。

此外，PoolMon 分析可能显示 Windows 通知设施（WnF）标记正在使用所有可用的分页池内存。

## 原因

此问题发生在终结点映射器逻辑组件中。

注意

远程注册表服务旨在停止在连接空闲 10 分钟后运行。

这是 Windows 中的设计行为。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 按 Windows 键+R 打开运行命令框。
2. 键入“regedit.exe”，然后按 Enter。
3. 找到以下注册表子项：  
   `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\RemoteRegistry`
4. 在详细信息窗格中（右侧），双击 DisableIdleStop。
5. 将值更改为00000001。

   注意

   默认值为 00000000。
6. 退出注册表编辑器。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/memory-leak-remote-registry-service)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
