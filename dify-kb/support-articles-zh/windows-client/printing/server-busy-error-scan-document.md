# 尝试扫描文档时出现“服务器繁忙”错误消息

本文提供了在尝试扫描文档时修复“服务器繁忙”错误的解决方法。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 2971655

## 现象

假设出现了下面这种情景：

- 你运行的是 64 位 （x64） 版本的 Windows 8.1、Windows 8 或 Windows 7。
- 运行 32 位扫描应用程序。
- 你使用的是使用 TWAIN 1.0 默认接口的扫描程序。
- 尝试扫描文档。

在此方案中，系统会提示你“你想要扫描什么？”消息。 消息窗口还显示用于配置扫描程序的选项。 几秒钟后，你会收到以下错误消息：

> 服务器忙

## 原因

出现此问题的原因是 32 位扫描应用程序在 64 位版本的 Windows 中运行。 在这种情况下，扫描程序的驱动程序在单独的Wiawow64.exe过程中加载。 “你想要扫描什么？”消息是 Wiawow64 过程的一部分。 错误消息是由来自 32 位扫描应用程序的 OLE 调用引起的。 出现此问题的原因是，OLE 调用的超时值在扫描应用程序正在等待“你想要扫描什么？”窗口中的用户输入时过期。

## 解决方法

若要解决此问题，建议与扫描应用程序供应商联系，让他们更新应用程序。

## 详细信息

如果你是开发人员，请参阅以下信息：

调用 AfxOleInit 时（）;函数， *m\_nTimeout* 参数设置为默认值 8 秒。 若要禁用 OLE 调用的超时，必须在调用 AfxOleInit（） 后添加以下行：功能：

> AfxOleGetMessageFilter（）->EnableNotRespondingDialog（FALSE）;

## 数据收集

如果需要Microsoft支持方面的帮助，建议按照使用 TSS 收集信息中的 [步骤收集用户体验问题](../windows-troubleshooters/gather-information-using-tss-user-experience#printing)来收集信息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/server-busy-error-scan-document)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
