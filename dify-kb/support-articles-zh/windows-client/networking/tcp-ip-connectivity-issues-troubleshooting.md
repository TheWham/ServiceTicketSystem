# TCP/IP 连接疑难解答

[试试我们的虚拟代理](https://vsa.services.microsoft.com/v1.0/?partnerId=7d74cf73-5217-4008-833f-87a1a278f2cb&flowId=DMC&initialQuery=31806409) - 它可以帮助快速识别和修复常见的 Active Directory 复制问题。

*适用于：* 支持的 Windows 客户端和 Windows Server 版本

本文提供了用于排查 TCP/IP 连接错误的综合指南。

## 症状和分析

可能会在应用程序级别遇到连接问题，或者可能会遇到超时错误。 以下是一些常见方案：

- 与数据库服务器的应用程序连接
- SQL 超时错误
- BizTalk 应用程序超时错误
- 远程桌面协议 （RDP） 失败
- 文件共享访问失败
- 常规连接

怀疑与网络相关的问题时，建议收集网络数据包捕获。 可以筛选此捕获，以确定有问题的 TCP 连接并确定失败的原因。

在故障排除过程中，可能会遇到网络捕获中的 TCP RESET，这可能指示网络问题。

## TCP 简介

TCP 被描述为面向连接的可靠协议。 它通过握手过程确保可靠性。 TCP 会话以三向握手启动，然后是数据传输，最后是四向关闭。

- 发送方和接收方都同意关闭会话的四向关闭称为正常关闭。 这由 TCP 标头中的 FIN 标志标识为 1。
- 四向关闭后，计算机在释放端口之前等待 4 分钟（默认情况下）。 这称为TIME\_WAIT状态。 在此TIME\_WAIT状态期间，可以处理 TCP 连接的任何挂起数据包。 TIME\_WAIT状态完成后，为连接分配的所有资源都会释放。
- TCP 重置是突然关闭的会话，导致立即释放已分配的资源并擦除所有连接信息。 这由 TCP 标头中的 RESET 标志标识为 1。
  在源和目标上同时收集的网络跟踪可帮助你确定流量流并确定故障点。

以下部分概述了可能发生 RESET 的方案。

## 通过网络丢失数据包

当 TCP 对等方发送数据包而不接收响应时，对等方将重新传输数据。 如果没有响应，会话以 ACK RESET 结束，表示应用程序确认交换的数据，但由于数据包丢失而关闭连接。

源和目标上的同时网络跟踪可以验证此行为。 在源端，可以看到重新传输的数据包。 在目标端，这些数据包不存在。 此方案指示源和目标之间的网络设备正在删除数据包。

### 方案 1：初始 TCP 握手期间数据包丢失

如果初始 TCP 握手由于数据包丢弃而失败，则默认情况下将重新传输 TCP SYN 数据包三次。

注意

重新传输 TCP SYN 数据包的次数可能因 OS 而异。 这由 TCP 全局**参数下**的最大 SYN 重新传输**值**确定，可以使用命令`netsh int tcp show global`查看该值。

假设 IP 地址为 10.10.10.1 的源计算机通过 TCP 端口 445 连接到 IP 地址为 10.10.10.2 的目标。 下面是源计算机上收集的网络跟踪的屏幕截图，其中显示了发送 TCP SYN 数据包的初始 TCP 握手，然后由源重新传输，因为未从目标接收任何响应。

![网络监视器中帧摘要的屏幕截图。](media/tcp-ip-connectivity-issues-troubleshooting/source-side-port-445.png)

在目标上收集的网络跟踪中看到的同一 TCP 会话显示目标未收到上述数据包。 这意味着 TCP SYN 数据包已通过中间网络丢弃。

![网络监视器中带有筛选器的帧摘要的屏幕截图。](media/tcp-ip-connectivity-issues-troubleshooting/destination-side-same-filter.png)

如果 TCP SYN 数据包到达目标，但目标未响应，请验证连接到的 TCP 端口是否处于目标计算机上的侦听状态。 这可以在命令 `netstat -anob`的输出中检查。

如果端口正在侦听，但仍没有响应，则 Windows 筛选平台（WFP）可能会有下降。

### 方案 2：建立 TCP 连接后数据传输期间的数据包丢失

在建立 TCP 连接后发送的数据包通过网络删除的情况下，默认情况下，TCP 会重新传输数据包五次。

假设具有 IP 地址 192.168.1.62 的源计算机已与 IP 地址为 192.168.1.2 的目标计算机建立了连接，该计算机通过 TCP 端口 445 建立 IP 地址 192.168.1.2。 源计算机正在发送五次重新传输的数据（SMB 协商数据包），如下所示。 未收到来自目标的响应后，源计算机将发送 ACK-RST 以关闭此 TCP 连接。

源 192.168.1.62 端跟踪：

![显示数据包端跟踪的屏幕截图。](media/tcp-ip-connectivity-issues-troubleshooting/source-192-168-1-62.png)

不会看到上述任何数据包到达目标。

你需要让内部网络团队调查源和目标之间的不同跃点，并检查是否有任何跃点可能导致数据包丢弃。

## TCP 标头中的参数不正确

当网络中的中间设备修改数据包时，会发生此行为，导致接收端的 TCP 拒绝它们。 例如，可能会更改 TCP 序列号，或者由具有修改后的 TCP 序列号的中介设备重播数据包。

源和目标上的同时网络跟踪有助于识别对 TCP 标头的任何修改。

首先比较源跟踪和目标跟踪，以检测数据包中的任何更改，或者存在代表源到达目标的新数据包。

在这种情况下，我们建议从内部网络团队寻求帮助，以确定正在修改或重播数据包到目标的任何设备。 常见的罪魁祸首包括 Riverbed 设备或 WAN 加速器。

## 应用程序级重置

如果确定重置不是由于数据包丢弃、参数错误或数据包修改（通过网络跟踪标识），则可以得出结论，问题是应用程序级重置。

应用程序级重置的特点是确认 （ACK） 标志设置为 1 以及重置 （R） 标志。 这表示服务器确认收到数据包，但出于某种原因不接受连接。 当接收数据包的应用程序发现数据中无法接受的内容时，通常会发生此问题。

在下面的屏幕截图中，可以看到源和目标上的数据包相同，无需修改或删除。 但是，目标将显式重置发送到源。

源端跟踪：

![网络监视器中源端数据包的屏幕截图。](media/tcp-ip-connectivity-issues-troubleshooting/screenshot-of-packets-on-source-side-in-network-monitor.png)

目标端跟踪：

![网络监视器中目标端数据包的屏幕截图。](media/tcp-ip-connectivity-issues-troubleshooting/screenshot-of-packets-on-destination-side-in-network-monitor.png)

发送 TCP SYN 数据包时，也会发生 ACK+RST 标记的 TCP 数据包。TCP SYN 数据包由源计算机启动，以在特定端口上建立连接。 但是，如果目标服务器出于任何原因不想接受数据包，则服务器会使用 ACK+RST 数据包进行响应。

![包含 ACK RSK 标志的数据包的屏幕截图。](media/tcp-ip-connectivity-issues-troubleshooting/ack-rst-flag-packet.png) 在这种情况下，必须调查导致重置（端口号标识）的应用程序，以了解连接重置的原因。

注意

上述信息与从 TCP 角度而不是 UDP 进行重置有关。 UDP 是一种无连接协议，数据包无法发送。 因此，在使用 UDP 作为传输协议时，不会观察到重新传输或重置。 但是，UDP 将 ICMP 用作错误报告协议。 当 UDP 数据包发送到目标中未列出的端口时，目标将立即响应 ICMP“**目标主机无法访问：端口无法访问**”消息。

```
10.10.10.1  10.10.10.2  UDP UDP:SrcPort=49875,DstPort=3343
 
10.10.10.2  10.10.10.1  ICMP    ICMP:Destination Unreachable Message, Port Unreachable,10.10.10.2:3343
```

在 TCP/IP 连接问题的故障排除过程中，你可能会在网络跟踪中观察到计算机接收数据包但未响应它们。 这可能表示目标服务器的网络堆栈下降。

若要确定本地 Windows 防火墙是否正在删除数据包，请使用以下命令在计算机上启用 Windows 筛选平台（WFP）的审核。

```
auditpol /set /subcategory:"Filtering Platform Packet Drop" /success:enable /failure:enable
```

然后，可以查看安全事件日志，以识别特定 TCP 端口和 IP 地址上的数据包丢弃，以及关联的 WFP 筛选器 ID。

![包含筛选器 ID 的事件属性的屏幕截图。](media/tcp-ip-connectivity-issues-troubleshooting/security-event-log.png)

接下来，运行生成*wfpstate.xml*文件的命令`netsh wfp show state`。

可以使用记事本打开此文件，并筛选事件日志中找到的 ID（例如，示例事件中的2944008）。 结果显示与阻止连接的筛选器 ID 关联的防火墙规则名称。

![wfpstate xml 文件的屏幕截图，其中包含与阻止连接的筛选器 ID 关联的防火墙规则名称。](media/tcp-ip-connectivity-issues-troubleshooting/wfpstate-file.png)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/tcp-ip-connectivity-issues-troubleshooting)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
