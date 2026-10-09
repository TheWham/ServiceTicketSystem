# 在 Windows 上触发 NMI 时NMI\_HARDWARE\_FAILURE错误

本文讨论在触发不可屏蔽中断（NMI）时发生NMI\_HARDWARE\_FAILURE错误的按设计行为。

*原始 KB 数：* 2750146

## 现象

在 Windows 计算机上，NMI 可能由用户手动按下计算机上的 NMI 开关或由于硬件错误而触发。

在这种情况下，Windows 停止执行并显示蓝屏，指出“你的电脑遇到了问题，需要重启。它包含以下错误代码：NMI\_HARDWARE\_FAILURE。

然后，计算机可以保存内存转储文件，并可能会自动重新启动，具体取决于系统控制面板下的“高级系统设置”中“启动和恢复”下指定的设置。

## 原因

与早期版本的 Windows 相比，遇到 NMI 时的行为发生了变化。 在 Windows 7、Windows Server 2008 R2 和早期版本中，当系统遇到 NMI 时，响应依赖于“NMICrashDump”注册表值的配置。
有关早期 Windows 版本中 NMICrashDump 注册表值和处理 NMIs 的详细信息，请单击以下文章编号以查看Microsoft知识库中的文章：  
[927069](https://support.microsoft.com/kb/927069) 如何在基于 Windows 的系统上使用 NMI 生成完整的故障转储文件或内核故障转储文件

在 Windows 8 和 Windows Server 2012 中，此行为不可配置。 NMI 将始终生成 bug 检查0x80（NMI\_HARDWARE\_FAILURE）。 这相当于早期 Windows 版本中存在“NMICrashDump”注册表值并设置为值 1 的行为。

## 详细信息

此行为是特意这样设计的。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/nmi-hardware-failure-error)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
