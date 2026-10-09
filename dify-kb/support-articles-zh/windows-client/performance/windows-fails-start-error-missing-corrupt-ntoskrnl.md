# 当启动期间按下键时，Windows 无法启动并出现错误丢失或损坏ntoskrnl.exe

本文提供了一种解决方法，说明在启动期间按下键时 Windows 无法启动并出现错误丢失或损坏ntoskrnl.exe的问题。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 2022960

## 现象

当你在启动计算机时按下或按住键盘上的键时，你可能会看到以下消息，Windows 将无法启动。

> Windows 无法启动，因为以下文件缺失或损坏：  
> <Windows root>\system32\ntoskrnl.exe。  
> 请重新安装上述文件的副本。

如果在启动期间未按任何键，则不会发生此问题。

注意

此问题可能发生在 Windows 7 之前的任意 Windows 操作系统上，同时发生在 32 位和 64 位平台上。

## 原因

出现此问题的原因是，在较小的时间范围内，按键可能会导致 Windows 初始化的一部分失败。

此问题不会导致任何损坏或数据丢失，ntoskrnl.exe文件未损坏，如错误消息所示。

## 解决方法

若要解决此问题，在显示 Windows 启动屏幕之前，请勿在启动期间按任何键。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/windows-fails-start-error-missing-corrupt-ntoskrnl)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
