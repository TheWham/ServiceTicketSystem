# 在 Windows Server 2008 R2 中为打印服务器使用 CNAME 记录时出现错误 0x00000709：操作无法完成

本文帮助修复错误 0x00000709（操作无法完成）。该错误在你为打印服务器使用 CNAME 记录时出现。

_原始 KB 编号：_ &nbsp; 2546625

## 症状

请考虑以下情形：

- 你的打印机托管在运行 Windows Server 2008 R2 的系统上。
- 你为打印服务器提供了一个备用 UNC 路径，并决定通过 DNS 中的 CNAME（别名）资源记录来实现。
- 客户端尝试使用 UNC 路径中的 CNAME 记录连接到打印机。

在此情形下，如果客户端在 UNC 路径中使用 CNAME 记录，则无法连接到打印机。此外，尝试连接到共享打印机会失败并出现以下错误：

> 操作无法完成（错误 0x00000709）。请仔细检查打印机名称，确保打印机已连接到网络。
> **备注**
>
> - 只要你使用实际主机名而不是 CNAME 记录，就可以成功连接到打印机。
> - 在按照 Microsoft 知识库以下文章中所述实施 DnsOnWire 注册表值之后，问题仍然存在：  
> [尝试使用别名（CNAME）资源记录连接到打印机时出现错误消息：Windows 无法连接到打印机](https://support.microsoft.com/help/979602)

## 原因

如果某些非 Microsoft DNS 解决方案为网络提供名称解析，则可能出现此问题。

## 解决方案

要解决此问题，请在打印服务器上按照下列步骤操作，然后重新启动后台打印程序（Print Spooler）服务：

1. 按照以下文章所述实施 `DnsOnWire` 注册表值：

   [尝试使用别名（CNAME）资源记录连接到打印机时出现错误消息：Windows 无法连接到打印机](https://support.microsoft.com/help/979602)

2. 编辑本地 Hosts 文件，在其中加入服务器的 CNAME 记录。
> **备注**
    > Hosts 文件条目必须以 NetBIOS 名称而不是 FQDN 的形式输入。

以下示例仅供说明。请使用对你网络有效的名称和 IP 地址。

使用 NetBIOS 名称： 192.168.0.10 CNAME

不要使用 FQDN： 192.168.0.10 `CNAME.CONTOSO.COM`

## 更多信息

如果非 Microsoft DNS 解决方案提供 ALL 类型的 `QRecord` 响应，则可能出现[症状](#症状)部分所述的问题。

## 数据收集

如果需要 Microsoft 支持部门的帮助，建议你按照[使用 TSS 收集用户体验问题的信息](https://learn.microsoft.com/en-us/troubleshoot/windows-client/windows-troubleshooters/gather-information-using-tss-user-experience#printing)中提到的步骤收集信息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/error-0x00000709-use-cname-record)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
