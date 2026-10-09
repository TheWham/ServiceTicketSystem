# 删除 Windows 10 中的网络组件时出现错误0x80071779

本文可帮助修复在卸载 **Microsoft Networks** 或其他网络组件客户端时发生的错误0x80071779。

*适用于：* 窗口 10 – 所有版本  
*原始 KB 数：* 4340181

## 现象

从 Windows 10 版本 1803 及基于更新的设备或计算机开始，无法卸载 **适用于 Microsoft Networks** 或其他网络组件的客户端。 看到以下错误消息：

> 无法卸载适用于 Microsoft Networks 功能的客户端。
>
> 错误0x80071779。

![0x80071779错误消息的屏幕截图。](media/cannot-uninstall-client-for-microsoft-networks/error-0x80071779.png)

## 原因

此为有意行为。

## 解决方法

Microsoft不支持使用此 GUI 或 **netcfg** 卸载协议或内置驱动程序。 相反，可以使用此 GUI 或 PowerShell cmdlet `Disable-NetAdapterBinding`从网络适配器取消绑定驱动程序。 这实际上与卸载驱动程序相同。

## 详细信息

如果要删除特定驱动程序，但当前不是可选功能的一部分，请在 [反馈中心](https://www.microsoft.com/store/productId/9NBLGGH4R32N)提交功能请求。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/cannot-uninstall-client-for-microsoft-networks)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
