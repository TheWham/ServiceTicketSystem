# 在 Windows 7 中更改系统显示缩放设置后，PNG 图像在 Word 2010 中无法正确打印

本文讨论在 Windows 7 中更改系统显示缩放设置后，PNG 图像在 Word 2010 中无法正确打印的问题。

*适用于：* Windows 7 Service Pack 1  
*原始 KB 数：* 3101023

## 现象

假设出现了下面这种情景：

- 你安装了一台基于 Windows 7 的计算机，该计算机已安装 Microsoft Word 2010。
- 你有一个包含 PNG 图像的 Word 文档。
- 在控制面板中，将 Windows 显示缩放从“小”-**100%（默认值）**更改为**“中等”-125%。**
- 在 Word 中，将文档打印到基于 XPS 的打印机驱动程序。

打印 Word 文档后，你会注意到 PNG 图像的边缘在打印输出上被切断。

## 原因

此问题可能是因为 PNG 图像不包含 pHY（物理像素尺寸）区块来指定图像中每个像素的大小。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 启动 Word 2010。
2. 右键单击 PNG 图像，然后单击“ **设置图片**格式”。
3. 更改任何 **“锐化”和“软化** ”或 **“亮度”和“对比度** ”滑块设置。
4. 单击“关闭**”**保存更改。
5. 再次右键单击 PNG 图像，然后将滑块设置还原到其原始位置。
6. 单击“关闭**”**保存更改。

图像设置中的此更改会将 pHYs 区块添加到 PNG 映像，并使它能够正确打印。

## 数据收集

如果需要Microsoft支持方面的帮助，建议按照使用 TSS 收集信息中的 [步骤收集用户体验问题](../windows-troubleshooters/gather-information-using-tss-user-experience#printing)来收集信息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/png-images-not-print-correctly-change-display-scaling)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
