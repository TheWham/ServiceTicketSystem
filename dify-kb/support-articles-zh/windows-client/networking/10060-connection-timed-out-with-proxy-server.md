# 慢速链路上代理服务器或 ISA Server 报 10060 连接超时错误

本文帮助解决在慢速、拥塞或高延迟 Internet 链路上，经由 Microsoft Proxy Server 或 ISA Server 时出现的 Winsock 超时错误。

_适用于：_ &nbsp; Windows 10 - 所有版本  
_原始 KB 编号：_ &nbsp; 191143

## 症状

在经由 Microsoft Proxy Server 或 ISA Server 的慢速、拥塞或高延迟 Internet 链路上，可能会出现 Winsock 超时错误。客户端 Web 浏览器中会显示以下 Winsock 错误消息：

> Proxy Reports:  
10060 Connection timed out
>
> 无法连接到 URL 中指定的 Web 服务器。请检查 URL 或重新尝试请求。

> **备注**
> 连接到不存在的 Internet 服务器时，或代理服务器计算机上配置了多个默认网关时，也可能出现超时错误。

## 解决方法

> **重要**
> 本部分（方法或任务）包含修改注册表的步骤。但是，如果修改注册表不当，可能会出现严重问题。因此，请务必仔细按照这些步骤操作。为增强保护，请在修改注册表之前先进行备份，以便在出现问题时可以还原注册表。有关如何备份和还原注册表的详细信息，请参阅[如何在 Windows 中备份和还原注册表](https://support.microsoft.com/help/322756)。

通过在注册表中添加子键来调整下面的 TCP/IP 设置，可以为连接的完成留出更多时间，从而减少超时次数。此设置默认情况下在注册表中不存在。

1. 启动注册表编辑器（Regedt32.exe），转到以下子项：  
    `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters`

2. 在"编辑"菜单上，单击"添加数值"，然后添加以下信息：

    - 数值名称：TcpMaxDataRetransmissions
    - 数值类型：REG_DWORD - 数字
    - 有效范围：0 - 0xFFFFFFFF
    - 默认数值：5（十进制）
    - 新数值：10（十进制）

3. 单击"确定"，然后退出注册表编辑器。
4. 修改注册表后重启计算机。

## 更多信息

TcpMaxDataRetransmissions 参数控制在终止连接之前，TCP 重发单个数据段（非连接段）的次数。连接上每连续重发一次，重传超时时间就翻一倍；响应恢复后会被重置。基本超时值是根据连接上测得的往返时间动态确定的。

此注册表项的默认值为 5；请将此值加倍为 10（十进制）（见上面步骤 2）。如果仍出现连接超时，可尝试再次加倍为 20（十进制）。

> **备注**
> 此注册表项只能减少连接超时错误发生的次数。要彻底解决此问题，可能需要对你的 Internet 连接或路由器进行更改。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/10060-connection-timed-out-with-proxy-server)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
