# 直接打印到打印机设置不适用于基于 XPS 的打印驱动程序

本文提供了一个解决方案，其中“ **直接打印到打印机** ”选项不适用于基于 XPS 的打印驱动程序。

*适用于：* Windows 7 Service Pack 1  
*原始 KB 数：* 3017432

## 现象

假设出现了下面这种情景：

- 在基于 Windows 7 Service Pack 1 的系统上，已安装使用基于 XPS 的打印驱动程序的打印机。
- **在打印机属性的“高级**”选项卡上，选择“**直接打印到打印机**”选项。

在此方案中，打印作业不会打印。

## 原因

选择“ **直接打印到打印机** ”选项时，必须在应用程序进程下呈现打印作业。 但是，使用基于 XPS 的打印驱动程序，打印作业将在PrintFilterPipelineSvc.exe进程中呈现。 因此，打印作业必须发送到后台处理程序，然后将它发送到要呈现的PrintFilterPipelineSvc.exe进程。

## 解决方法

若要解决此问题，请使用以下某种方法：

- 将打印机配置为使用后台处理程序。
- 使用基于 GDI 的打印驱动程序。

## 详细信息

Windows 8 和 Windows 8.1 使用基于 v4 XPS 的新打印机模型。 因此，“ **直接打印到打印机** ”选项不可用（显示为灰色）。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/print-directly-to-the-printer-setting-not-work)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
