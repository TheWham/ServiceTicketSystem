# 如果在基于 Windows 8.1 的计算机上使用 Intel 和 AMD 图形适配器，请停止错误0x113

本文提供了一种解决方法，用于解决计算机崩溃并出现错误代码0x113的问题。

*适用于：* Windows 8.1  
*原始 KB 数：* 2990029

## 现象

假设你有一台基于 Windows 8.1 的计算机，该计算机具有使用 Intel 和 AMD 图形适配器的混合图形配置。 在这种情况下，计算机在尝试从备用状态恢复时偶尔会崩溃，并收到以下错误消息：Bug 检查0x113（VIDEO\_DXGKRNL\_FATAL\_ERROR）

## 原因

出现此问题的原因是 AMD 驱动程序不支持运行时电源管理（RTPM），但 Intel 驱动程序支持 RTPM。

## 解决方法

若要解决此问题，请在 Intel 驱动程序中禁用 RTPM。

## Status

Microsoft 已经确认这是一个列于“适用范围”部分的 Microsoft 产品问题。

**第三方信息免责声明**

本文中提到的第三方产品由 Microsoft 以外的其他公司提供。 Microsoft 不对这些产品的性能或可靠性提供任何明示或暗示性担保。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/error-0x113-intel-amd-graphics-adapters)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
