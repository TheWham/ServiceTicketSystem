# 停止错误0xE6：如果启用了 DMAr，则重复禁用并启用无线设备驱动程序后DRIVER\_VERIFIER\_DMA\_VIOLATION

本文可帮助修复停止错误0xE6：在重复禁用和启用无线设备驱动程序后发生的DRIVER\_VERIFIER\_DMA\_VIOLATION。

*适用于：* Windows 10 版本 2004、Windows 10 版本 1909、Windows 10 版本 1903  
*原始 KB 数：* 4576784

## 现象

你正在对 WINDOWS 10 的 OEM 版本的无线设备驱动程序进行压力测试或故障排除。 驱动程序使用直接内存访问重新映射（DMAr）。

作为测试的一部分，你反复禁用和启用无线驱动程序（例如，在设备管理器）。 在多个此类周期之后，你会注意到系统操作速度变慢。 连续禁用和启用驱动程序 30 分钟后，设备内存不足，完全停止响应。

如果尝试使用 [驱动程序验证程序](/zh-cn/windows-hardware/drivers/devtest/driver-verifier) 工具分析问题，Windows 10 设备将遇到“停止”错误（也称为 bug 检查或蓝屏错误）。 错误代码 [0xE6：DRIVER\_VERIFIER\_DMA\_VIOLATION](/zh-cn/windows-hardware/drivers/debugger/bug-check-0xe6--driver-verifier-dma-violation)。

## 原因

出现此问题的原因是，DMA 适配器分配的内存在启用 DMA 重新映射时未正确分配。

## 解决方法

重要

应仅在测试环境中使用此解决方法。

若要解决此问题，请按照以下步骤禁用 DMA 重新映射：

1. 重启计算机，并在启动时按 F10（或任何由制造商指定的键）访问 BIOS 设置。
2. 选择 **“高级**>**系统选项”**，然后清除 **DMA 保护** 设置。

## Status

这是一个已知问题。 Microsoft正在开发计划包含在将来的 Windows 版本中的修补程序。

## 详细信息

- [为设备驱动程序启用 DMA 重新映射](/zh-cn/windows-hardware/drivers/pci/enabling-dma-remapping-for-device-drivers)
- [DEVPKEY\_Device\_DmaRemappingPolicy](/zh-cn/windows-hardware/drivers/install/devpkey-device-dmaremappingpolicy)
- [KB 244617：使用驱动程序验证程序识别高级用户的 Windows 驱动程序的问题](https://support.microsoft.com/help/244617/using-driver-verifier-to-identify-issues-with-windows-drivers-for-adva)
- [bug 检查0xE6：DRIVER\_VERIFIER\_DMA\_VIOLATION](/zh-cn/windows-hardware/drivers/debugger/bug-check-0xe6--driver-verifier-dma-violation)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/stop-error-0xe6-wireless-device-driver-dmar)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
