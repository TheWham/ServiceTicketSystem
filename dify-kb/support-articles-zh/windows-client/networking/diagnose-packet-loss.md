# 诊断数据包丢失

每当网络数据包未到达其预期目标时，就会出现数据包丢失。 某些数据包丢失是正常的，并不总是会导致更高级别的网络问题。 在其他情况下，数据包丢失可能会降低性能，并导致应用程序编程接口（API）或应用程序失败。

## 捕获和诊断数据包丢失

执行数据包丢失调查的第一步是捕获 [数据包监视器（Pktmon）](/zh-cn/windows-server/networking/technologies/pktmon/pktmon) 跟踪，通常是使用 pktmon 命令行工作流。 Pktmon 可以捕获数据包跟踪、将本地数据包丢失归因于特定原因和代码位置，以及收集数据包丢失统计信息。 与 [Wireshark](https://www.wireshark.org/) 分析协议级别行为相结合时，pktmon 跟踪足以识别许多数据包丢失情况的根本原因。

如果 pktmon 诊断结果不确定，可以分别使用 `netsh.exe trace start scenario=InternetClient` 命令用于客户端方案或 `netsh.exe trace start scenario=InternetServer` 命令用于服务器方案，以捕获更详尽的组件级跟踪。 捕获事件后，使用 `netsh.exe trace stop` 命令停止跟踪。 这些组件级别的跟踪既嘈杂又不清晰，但通常在本地数据包丢弃之前或之后包含额外的上下文。 对于远程丢失，它们可能指示本地系统推断数据包丢失的发生。 跟踪可以使用`netsh.exe trace convert nettrace.etl`转换为文本，可以在[Windows 性能分析器](/zh-cn/windows-hardware/test/wpt/windows-performance-analyzer)中打开，也可以用于任何其他 Windows 事件跟踪（ETW）工具。

如果怀疑网络接口卡（NIC）是数据包丢失的原因，可以通过任何 [性能计数器](/zh-cn/windows-server/networking/technologies/network-subsystem/net-sub-performance-counters) 接口或 [Get-NetAdapterStatistics](/zh-cn/powershell/module/netadapter/get-netadapterstatistics) cmdlet 监视其丢弃计数器。

## 本地数据包丢失的常见原因

本地数据包丢失是完全可观测的，可能是由各种内部和外部因素引起的。

- 本地策略

  检查软件可能会导致默认删除来自远程计算机的数据包，例如，当 Windows 防火墙拒绝入站连接尝试时。 系统上的网络安全或反恶意软件也可能导致这些问题。
- 资源不足

  如果系统或套接字耗尽资源来处理数据包，则会丢弃数据包。 资源限制的示例包括系统上的物理内存和套接字发送或接收缓冲区。 根据资源限制，这些事件可能仅持续微秒，例如，当系统的 CPU 无法足够快地对完整接收缓冲区做出反应时。
- ARP 或 ND 故障

  如果出站数据包的下一跃点未响应地址解析协议（ARP）或邻居发现（ND）请求，则会在本地系统上丢弃发送到该下一跃点的数据包。 如果超出 ARP 或 ND 数据包队列限制，则在 ARP 或 ND 进程期间也可能丢弃数据包。 ARP 或 ND 数据包本身通常不会在本地删除，并且属于远程数据包丢失类别。
- 无路由

  如果网络层找不到到目标的有效路由，可能会丢弃数据包。
- 数据包无效

  如果数据包标头无效，可能会删除数据包。 例如，数据包标头包含无效的校验和或字段值。

## 远程数据包丢失的常见原因

当数据包被丢弃时，本地计算机无法直接观测到远程的丢包现象。 互联网协议（IP）及其下的大多数层都是“尽力而为”且不可靠的。 如果需要对数据包丢失的复原能力， [端到端原则](https://en.wikipedia.org/wiki/End-to-end_principle) 要求终结点在其协议中实现可靠性。 在某些情况下，网络或远程终结点发送特定于协议的错误消息，指示丢失的原因。 但是，在许多情况下，数据包丢失的唯一迹象是缺少响应。

- 拥塞

  丢包检测拥塞控制算法会不断加快发送速度，直到发生数据包丢失。 如果算法推断丢失是由 [拥塞](https://en.wikipedia.org/wiki/Network_congestion)引起的，则它会暂时降低在响应中发送的速度。 这些算法需要少量的损失来提供反馈信号。
- 远程策略

  网络或远程计算机可能会根据自己的策略删除数据包。
- 目标无法访问

  如果远程计算机没有绑定到远程端口的套接字、网络无法找到到达远程计算机的连接路径，或远程计算机处于离线状态，则可能会出现这种情况。
- 会话丢失

  如果网络（包括有状态网络地址转换（NAT）、防火墙和负载均衡器）或远程计算机重置或最近未收到数据包，则其会话上下文可能会过期，并且会丢弃后续数据包。
- 最大传输单元（MTU）下降

  如果数据包的大小超出了沿着路径到远程计算机的网络链路的最大传输大小，可能由于 MTU 缩减而产生错误：需要进行 Internet 控制消息协议（ICMP）分片或数据包过大。

## 数据包监视器跟踪示例

运行以下命令：

```
pktmon.exe start -c
pktmon.exe stop
pktmon.exe etl2txt PktMon.etl
```

生成的 **PktMon.txt** 文件包含类似于以下内容的行：

```
[30]0000.0000::<DateTime> [Microsoft-Windows-PktMon] Drop: PktGroupId 8444249301423149, PktNumber 1, Appearance 0, Direction Rx , Type IP , Component 49, Filter 1, DropReason INET: transport endpoint was not found , DropLocation 0xE000460A, OriginalSize 402, LoggedSize 148
       Drop: ip: 192.168.5.88.50005 > 192.168.5.68.50005: UDP, length 374
```

此信息指示发往端口 50005 的入站 UDP 数据包已删除，因为没有本地套接字绑定到该端口。

## Network Shell 跟踪示例

运行以下命令：

```
netsh.exe trace start scenario=InternetClient
netsh.exe trace stop
netsh.exe trace convert NetTrace.etl
```

生成的 **NetTrace.txt** 文件包含类似于以下内容的行：

```
[30]0000.0000::<DateTime> [Microsoft-Windows-TCPIP]TCPIP: Network layer (Protocol 1(ICMP), AddressFamily = 2(IPV4)) dropped 1 packet(s) on interface 13. SourceAddress = 192.168.5.68. DestAddress = 192.168.5.88. Reason = 9(Inspection drop). Direction = 0(Send). NBL = 0xFFFFE189BEAF3AC0.
```

此信息表明出站 ICMP 数据包因 Windows 筛选平台（WFP）检查而被丢弃。 粮食计划署的下一步是按照 [粮食计划署的实时投递故障排除步骤](/zh-cn/windows/security/operating-system-security/network-security/windows-firewall/troubleshooting-uwp-firewall#debugging-live-drops)。

在另一种方案中，远程终结点未确认以前发送的 TCP 段，最终会触发本地重新传输计时器，导致 TCP 重新发送某些可能丢失的数据：

```
[31]0000.0000::<DateTime> [Microsoft-Windows-TCPIP]TCP: Connection 0xFFFFE189BD811AA0 0(RetransmitTimer) timer has expired.
[31]0000.0000::<DateTime> [Microsoft-Windows-TCPIP]TCP: Tail Loss Probe Event Connection = 0xFFFFE189BD811AA0, Event = 2(TimerFired).
[31]0000.0000::<DateTime> [Microsoft-Windows-TCPIP]TCP: Tail Loss Probe Send Connection = 0xFFFFE189BD811AA0 SndUna = 2526318360, SndMax = 2526321759, SendAvailable = 3399, TailProbeSeq = 2526320299, TailProbeLast = 2526321759, ControlsToSend = 0, ThFlags = 16.
[31]0000.0000::<DateTime> [Microsoft-Windows-TCPIP]TCP: connection 0xFFFFE189BD811AA0 (local=192.168.5.68:55330 remote=6.6.0.27:443): TCP send event, SeqNo = 2526320299, BytesSent = 1460, CWnd = 18538, SndWnd = 197632, SRtt = 17631, RttVar = 4947, RTO = 300, RcvWnd = 65535, PacingRate = 0, State = 4(EstablishedState), CongestionState = 0, SndUna = 2526318360, SndMax = 2526321759, RecoveryMax = 0, RcvBufSet = 0(FALSE), MaxRcvBuf = 65535.
[31]0000.0000::<DateTime> [Microsoft-Windows-TCPIP]TCP: connection = 0xFFFFE189BD811AA0 send tracker marked a transmit as rexmit. Start = 2526320299, End = 2526321759, Timestamp = 467744252, InFlightCount = 2, SackedBytes = 0, BytesInFlight = 4859.
[31]0000.0000::<DateTime> [Microsoft-Windows-TCPIP]TCP: Connection 0xFFFFE189BD811AA0 0(RetransmitTimer) timer started. Scheduled to expire in 300 ms. Processor 31: LastInterruptTime 305324952689 100-ns ticks; LastMicrosecondCount 30532515324 msec
```

## 详细信息

- [TCP/IP 连接故障排除](tcp-ip-connectivity-issues-troubleshooting)
- [如何捕获 NetLog 日志](https://www.chromium.org/for-testers/providing-network-details)
- [如何收集网络跟踪](/zh-cn/azure/azure-web-pubsub/howto-troubleshoot-network-trace)
- [检查网络活动](/zh-cn/microsoft-edge/devtools-guide-chromium/network/)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/diagnose-packet-loss)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
