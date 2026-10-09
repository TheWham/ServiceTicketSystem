# 使用 CNAME 记录连接到共享打印机时出错

本文提供了使用 CNAME 记录连接到共享打印机时修复错误的解决方法。

*适用于：* Windows Server 2012 R2、Windows 7 Service Pack 1  
*原始 KB 数：* 2965564

## 总结

本文介绍使用 CNAME 记录连接到共享打印机时发生的两条错误消息。

## 现象

### 错误 1

为基于 Windows Server 2008 R2 的打印机服务器提供替代的通用命名约定 UNC （UNC） 路径。 UNC 路径使用 CNAME DNS 记录。 客户端尝试连接到打印机时收到以下错误消息：

> 无法完成操作（错误0x00000709）。 仔细检查打印机名称，并确保打印机已连接到网络。

有关此问题的详细信息，请单击以下文章编号以查看 Microsoft 知识库中的文章：

> 在 Windows Server 2008 R2 中使用打印服务器的 CNAME 记录时，2546625“操作无法完成（错误0x00000709）”错误

### 错误 2

当你使用 CNAME DNS 记录连接到运行 Windows Server 2008 R2 或 Windows 7 的打印机服务器时，客户端会收到以下错误消息：

> Windows 无法连接到打印机。 检查打印机名称，然后重试。 如果这是网络打印机，请确保打印机处于打开状态，并且打印机地址正确。

有关此问题的详细信息，请单击以下文章编号以查看 Microsoft 知识库中的文章：

> [尝试使用别名（CNAME）资源记录连接到打印机时979602](https://support.microsoft.com/help/979602) 错误消息：“Windows 无法连接到打印机”

## 解决方法

若要解决这些问题，请使用以下命令：

```
reg add hklm\system\currentcontrolset\control\print /v DnsOnWire /t REG_DWORD /d 1
reg add hklm\system\currentcontrolset\services\lanmanserver\parameters /v DisableStrictNameChecking /t REG_DWORD /d 1
reg add hklm\system\currentcontrolset\services\lanmanserver\parameters /v OptionalNames /t REG_SZ /d " aliasname "
```

注意

对于第三方 DNS 提供程序，可能需要使用 QWord 而不是 DWord。 因此，应对这些命令使用 QWord 而不是 DWord。

## 数据收集

如果需要Microsoft支持方面的帮助，建议按照使用 TSS 收集信息中的 [步骤收集用户体验问题](../windows-troubleshooters/gather-information-using-tss-user-experience#printing)来收集信息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/errors-connect-to-shared-printer-cname-record)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
