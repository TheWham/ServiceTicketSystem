# 排查 DNS 客户端名称解析问题

本文可帮助排查域名系统（DNS）客户端名称解析问题。

以下三个主要原因可能会导致域名系统（DNS）解决问题：

- DNS 客户端问题或配置。
- DNS 服务器问题或配置。
- DNS 客户端和 DNS 服务器之间的中间设备或配置，或者 DNS 服务器与外部解析程序（例如根提示、转发器和条件转发器）之间，这可能需要进一步调查。

注意

本文重点介绍 DNS 客户端问题或配置导致的 DNS 解析问题。 有关 DNS 服务器问题的信息，请参阅 [DNS 服务器](/zh-cn/windows-server/networking/dns/troubleshoot/troubleshoot-dns-server)疑难解答。

DNS 解析问题可能发生在以下情况下：

## 方案 1：防火墙规则阻止 UDP 端口 53 上的出站连接

假设存在阻止用户数据报协议（UDP）端口 53 上的出站连接的出站防火墙规则。

在这种情况下，当运行 PowerShell cmdlet 并[运行 `Resolve-DnsName contoso.com` Wireshark](https://www.wireshark.org/) 时，会收到以下错误：

```
resolve-dnsname : contoso.com : This operation returned because the timeout period expired
At line:1 char:1
+ resolve-dnsname contoso.com
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : OperationTimeout: (contoso.com:String) [Resolve-DnsName], Win32Exception
    + FullyQualifiedErrorId : ERROR_TIMEOUT,Microsoft.DnsClient.Commands.ResolveDnsName
```

检查 Wireshark 跟踪时，域控制器（DC）没有出站 DNS 流量。

在这种情况下，请查看 Windows 防火墙规则，并检查 UDP 或传输控制协议 （TCP） 端口 53 上的数据包丢弃的任何第三方安全产品。

如果注意到 DNS 解析请求没有响应，则使用端口镜像从交换机收集 Wireshark 跟踪有助于确认 DNS UDP 数据包离开客户端计算机。 请求如下所示：

```
139 3.149039    10.0.1.10   10.0.1.2    DNS 71  Standard query 0xcdc6 A contoso.com
140 3.149192    10.0.1.10   10.0.1.2    DNS 71  Standard query 0x8168 AAAA contoso.com
```

这些是主机 A 和主机 AAAA 的标准查询请求，没有响应。 检查跟踪可以隔离问题。 如果在交换机上看到 UDP 数据包，则表示数据包已离开客户端计算机，并且问题超出了客户端计算机。

## 方案 2：Hosts 文件中有一个域名条目

假定位于 **C：\Windows\System32\drivers\etc** 的 Hosts 文件具有要解析的域名的条目。 例如：

`192.168.1.10` `contoso.com`

在这种情况下，使用 Wireshark 运行解析域名 `contoso.com` 时，会收到以下输出：

```
PS C:\Windows\System32\drivers\etc> Resolve-DnsName contoso.com

Name                                           Type   TTL   Section    IPAddress
----                                           ----   ---   -------    ---------
contoso.com                                    A      60440 Answer     192.168.1.10
```

此外，在 Wireshark 中无法检测到任何流量。

这是因为 DNS 客户端在解析名称时使用以下序列：

1. 检查缓存。
2. 检查 Hosts 文件。
3. 将查询发送到 DNS 服务器。

由于 Hosts 文件中有一个条目，因此 DNS 客户端服务不会查询 DNS 服务器。

## 方案 3：客户端指向不正确的或无法访问的 DNS 服务器

假设 DNS 客户端的网络接口卡（NIC）上的 DNS 服务器配置了无法访问 DNS 服务器的 IP。 客户端 IP 配置如以下示例所示：

```
IPv4 Address. . . . . . . . . . . : 10.0.1.10<Preferred>
Default Gateway . . . . . . . . . : 10.0.1.1
DNS Servers . . . . . . . . . . . : 192.168.0.1
```

由于 DNS 服务器无法访问，客户端不会收到响应，导致查询超时。可以在 Wireshark 中观察到这次超时。 没有响应的 DNS 标准查询：

```
439 14.482923   10.0.1.10   192.168.0.1 DNS 71  Standard query 0xa384 A contoso.com
440 14.482923   10.0.1.10   192.168.0.1 DNS 71  Standard query 0x4fe0 AAAA contoso.com
```

在这种情况下，运行 `Resolve-DnsName contoso.com` PowerShell cmdlet 时，会收到以下输出：

```
PS C:\Windows\System32\drivers\etc> Resolve-DnsName contoso.com
Resolve-DnsName : contoso.com : This operation returned because the timeout period expired
At line:1 char:1
+ Resolve-DnsName contoso.com
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : OperationTimeout: (contoso.com:String) [Resolve-DnsName], Win32Exception
    + FullyQualifiedErrorId : ERROR_TIMEOUT,Microsoft.DnsClient.Commands.ResolveDnsName
```

## 方案 4：NIC 上配置了多个 DNS 服务器，其中一些服务器无法访问

假设客户端 DNS 设置配置了一些无法访问的 DNS 服务器，如下所示：

```
DNS Servers . . . . . . . . . . . : 192.168.0.1
                                    172.16.1.1
                                    192.168.1.20
                                    10.0.1.2
```

在这种情况下，使用 `Resolve-DnsName contoso.com` PowerShell cmdlet 执行 DNS 解析时，除了 `10.0.1.2` 无法访问所有这些 DNS 服务器地址。

根据设计，DNS 客户端将开始将此查询发送到按特定顺序配置的 DNS 服务器，并等待特定宽限期内的响应。

可以在 Wireshark 中使用筛选器 `dns.qry.name == contoso.com`查看此过程。

Wireshark 输出显示查询需要近 4 秒才能完成。 从网络的角度来看，此持续时间可能很长，可能会导致某些应用程序超时。

```
30  03:56:58.634623 10.0.1.10   192.168.0.1  DNS 71  Standard query 0x9f32 A contoso.com
33  03:56:59.643171 10.0.1.10   172.16.1.1   DNS 71  Standard query 0x9f32 A contoso.com
38  03:57:02.646443 10.0.1.10   192.168.0.1  DNS 71  Standard query 0x9f32 A contoso.com
42  03:57:02.646556 10.0.1.10   172.16.1.1   DNS 71  Standard query 0x9f32 A contoso.com
43  03:57:02.646573 10.0.1.10   192.168.1.20 DNS 71  Standard query 0x9f32 A contoso.com
47  03:57:02.646684 10.0.1.10   10.0.1.2     DNS 71  Standard query 0x9f32 A contoso.com
```

注意

在此方案中，使用 `nslookup` 不适用，并且始终会失败。 这是因为 `nslookup` 使用 **nslookup.exe** 仅联系配置的主 DNS 服务器，在本例中为 `192.168.0.1`< a0/&nslookup.exe。

## 方案 5：长 DNS 后缀搜索列表

假设 DNS 客户端上的 DNS 后缀搜索列表配置如下：

注意

`contoso.com` 是正确的 DNS 后缀。

```
DNS Suffix Search List. . . . . . : microsoft.com
                                    ms.com
                                    azure.com
                                    ms.local
                                    contoso.local
                                    contoso.com
```

在这种情况下，使用 `Resolve-DnsName internal` PowerShell cmdlet 执行名称解析时，DNS 客户端将按顺序追加 DNS 后缀，如果列表中所需的查询较低，可能会导致延迟。 通过使用 Wireshark 中的筛选器 `dns.qry.name contains internal` ，查询如下所示：

```
116 04:33:38.164251 10.0.1.10   10.0.1.2    DNS 82  Standard query 0xc557 A internal.microsoft.com
120 04:33:38.177186 10.0.1.10   10.0.1.2    DNS 75  Standard query 0x0a4b A internal.ms.com
124 04:33:38.453625 10.0.1.10   10.0.1.2    DNS 78  Standard query 0x4245 A internal.azure.com
128 04:33:38.466154 10.0.1.10   10.0.1.2    DNS 77  Standard query 0xfaca A internal.ms.local
131 04:33:38.471033 10.0.1.10   10.0.1.2    DNS 82  Standard query 0xa9d6 A internal.contoso.local
136 04:33:38.476248 10.0.1.10   10.0.1.2    DNS 80  Standard query 0x611f A internal.contoso.com
```

注意

如果需要测试特定查询，可以在末尾添加尾随句点（.）。 例如： `internal.contoso.com.`

## 测量 DNS 解析查询需要多长时间

若要测量 DNS 解析查询完成所需的时间，请运行以下 PowerShell cmdlet：

注意

一秒以下的结果被视为可接受的。

```
(Measure-Command {Resolve-DnsName -Name contoso.com -Server <IP Address> -DnsOnly}).TotalMilliseconds
```

**第三方信息免责声明**

本文中提到的第三方产品由 Microsoft 以外的其他公司提供。 Microsoft 不对这些产品的性能或可靠性提供任何明示或暗示性担保。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/troubleshoot-dns-client-resolution-issues)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
