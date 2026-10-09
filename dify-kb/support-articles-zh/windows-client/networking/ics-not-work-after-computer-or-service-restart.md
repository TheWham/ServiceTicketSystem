# 在 Windows 10 中重启计算机或服务后，ICS 不起作用

本文提供了一种解决方案，用于解决 Internet 连接共享（ICS）设置丢失且 ICS 连接在重启 ICS 服务或运行 Windows 10 版本 1709 的计算机后不起作用的问题。

*适用于：* Windows 10 版本 1709  
*原始 KB 数：* 4055559

## 现象

假设出现了下面这种情景：

- 你有一台基于 Windows 10 版本 1709 的计算机，该计算机具有两个连接到两个不同的网络的网络接口。
- 将 ICS 服务启动类型更改为 **“自动**”。
- 可以在其中一个网络接口上启用 ICS，然后确认 ICS 连接正常工作。
- 重启 ICS 服务或计算机。

在此方案中，ICS 设置会丢失，ICS 连接不起作用。

注意

通常，如果 ICS 上没有流量 4 分钟，服务会关闭，并且不会自动重启。

## 解决方案

注意

- 如果使用注册表编辑器或使用其他方法错误地修改了注册表，则可能会发生严重问题。 这些问题可能需要重新安装操作系统才能解决。 Microsoft 不能保证可以解决这些问题。 您应自行承担修改注册表的风险。
- 此解决方案目前仅在安装了更新 KB 4054517 的 Windows 10 版本 1709 中提供。

若要解决此问题，请设置以下注册表子项，然后将 ICS 服务启动模式更改为 **“自动**”：

- 路径：`HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\SharedAccess`
- 类型：DWORD
- 设置：EnableRebootPersistConnection
- 值：1

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/ics-not-work-after-computer-or-service-restart)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
