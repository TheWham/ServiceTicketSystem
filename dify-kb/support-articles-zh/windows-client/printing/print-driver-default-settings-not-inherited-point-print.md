# 打印驱动程序默认设置不会通过 Windows 10 版本 1709 中的“点和打印”继承

本文提供了一个解决方案，其中打印驱动程序默认设置不是通过 Windows 10 版本 1709 中的“点和打印”继承的问题。

*适用于：* Windows Server 2019、Windows Server 2016、Windows 10 版本 1709  
*原始 KB 数：* 4052855

## 现象

假设出现了下面这种情景：

- 你有一个运行 Windows 10 版本 1709 或 Windows Server 版本 1709 的客户端。
- 你有一个运行 Windows Server 2016、Windows Server 2012 或 Windows Server 2012 R2 或 Windows Server 2008 R2 的打印服务器。
- 使用“点和打印”过程安装打印机驱动程序。

在此方案中，客户端不会从打印服务器继承默认设置。

## 原因

出现此问题的原因是打印服务器和客户端之间的通用驱动程序（或 PScript5 驱动程序）不匹配。

## 解决方法

若要解决此问题，请按照以下步骤在客户端上手动设置打印机设置：

1. 右键单击“ **开始** ”按钮，然后选择“ **设置**”。
2. 选择“设备” 。
3. 在“设备”窗口的中心**，选择“**设备和打印机**”。**
4. 在 **“设备和打印机”** 窗口中，右键单击从服务器计算机安装的打印机图标。 然后选择“ **打印首选项**”。

   注意

   此时将 **打开“打印首选项** ”对话框。
5. 在对话框中，选择“ **高级** ”按钮。

   注意

   此时会打开“ **高级选项** ”对话框。 可以在此对话框中更改打印机设置。

## Status

Microsoft已确认，这是“适用于”部分中列出的Microsoft产品中的问题。

此问题已在 Windows 10 版本 1803 和 Windows Server 版本 1803 中修复。

## 数据收集

如果需要Microsoft支持方面的帮助，建议按照使用 TSS 收集信息中的 [步骤收集用户体验问题](../windows-troubleshooters/gather-information-using-tss-user-experience#printing)来收集信息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/print-driver-default-settings-not-inherited-point-print)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
