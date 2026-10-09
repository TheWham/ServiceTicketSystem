# 在 UEFI 中启用了KB4568831或更高版本的更新和增强的 Windows 生物识别安全性的 Lenovo ThinkPad 上停止错误

本文介绍导致 Lenovo ThinkPad 上的停止错误的问题，该错误KB4568831或更高版本的更新。

*适用于：* Windows 10 版本 2004  
*原始 KB 数：* 4580649

## 现象

你有一个 Lenovo ThinkPad 设备，该设备已收到 [2020 年 7 月 31 日-KB4568831（OS 内部版本 19041.423）预览](https://support.microsoft.com/help/4568831/windows-10-update-kb4568831) 更新或更新更新。 该设备还在 UEFI 中启用了增强的 Windows 生物识别安全性，并运行 Lenovo Vantage 软件。

设备遇到“停止”错误（也称为 bug 检查或蓝屏错误）。 与错误关联的代码是“SYSTEM\_THREAD\_EXCEPTION\_NOT\_HANDLED”（在“停止错误消息”屏幕）和“0xc0000005访问被拒绝”（内存转储文件和其他日志中）。 关联的进程ldiagio.sys。

## 原因

接收 [2020 年 7 月 31 日 KB4568831（OS 内部版本 19041.423）预览](https://support.microsoft.com/help/4568831/windows-10-update-kb4568831) 版或更新更新的 Windows 设备限制进程在特定条件下访问 [外围组件互连（PCI）设备配置空间](/zh-cn/windows-hardware/drivers/pci/accessing-pci-device-configuration-space) 的方式。 必须访问 PCI 设备配置空间的进程必须使用官方支持的机制。

在 2019 或 2020 年制造的 UEFI 中启用增强型 Windows 生物识别安全性选项，满足触发此行为的条件。 Lenovo Vantage 软件运行时，某些版本可能会尝试以不受支持的方式访问 PCI 设备配置空间。 此操作会导致发生“停止”错误。

## 解决方法

若要暂时缓解此问题，请编辑设备 UEFI 配置（在**“安全>虚拟化**”部分中），以禁用增强型 Windows 生物识别安全性。 此更改禁用 SDEV 表和 VBS 启用的限制。

## Status

联想和Microsoft正在努力解决此问题。 有关此问题的已更新 Lenovo Vantage 支持信息，请参阅 [Lenovo HT511000](https://support.lenovo.com/ca/en/solutions/ht511000)。

## 详细信息

接收 [2020 年 7 月 31 日 KB4568831（OS 内部版本 19041.423）预览](https://support.microsoft.com/help/4568831/windows-10-update-kb4568831)版或更高版本更新的 Windows 设备限制进程在安全设备（SDEV）ACPI 表[存在且](https://uefi.org/sites/default/files/resources/ACPI_6_2.pdf)[基于虚拟化的安全（VBS）](/zh-cn/windows-hardware/design/device-experiences/oem-vbs)正在运行时如何访问外围组件互连（PCI）设备配置空间。 必须访问 PCI 设备配置空间的进程必须使用官方支持的机制。

SDEV 表在 ACPI 中定义安全硬件设备。 如果启用了使用虚拟化的安全功能，则会在系统上启用 VBS。 这些功能的一些示例包括虚拟机监控程序代码完整性或 Windows Defender Credential Guard。

新的限制旨在防止恶意进程修改安全设备的配置空间。 设备驱动程序或其他系统进程不得尝试操作任何 PCI 设备的配置空间，除非使用 [Microsoft提供的总线接口](/zh-cn/windows-hardware/drivers/ddi/wdm/ns-wdm-_bus_interface_standard) 或 [IRP](/zh-cn/windows-hardware/drivers/kernel/irp-mn-read-config)。 如果进程尝试以不受支持的方式访问 PCI 配置空间（例如，通过分析 MCFG 表并将配置空间映射到虚拟内存），Windows 将拒绝访问进程并生成停止错误。

在 2019 年和 2020 年制造的 UEFI 中启用增强的 Windows 生物识别安全性选项可启用 SDEV 表。 Lenovo Vantage 软件运行时，某些版本可能会尝试以不受支持的方式访问 PCI 设备配置空间。 此操作会导致停止错误。 此错误通常如“症状”部分中所述显示。

**第三方信息免责声明**

本文中提到的第三方产品由 Microsoft 以外的其他公司提供。 Microsoft 对这些产品的性能和可靠性不作任何明示或默示担保。

**第三方联系人免责声明**

Microsoft 会提供第三方联系信息来帮助你查找有关本主题的其他信息。 此联系信息可能会更改，恕不另行通知。 Microsoft 不保证第三方联系信息的准确性。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/stop-error-lenovo-thinkpad-kb4568831-uefi)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
