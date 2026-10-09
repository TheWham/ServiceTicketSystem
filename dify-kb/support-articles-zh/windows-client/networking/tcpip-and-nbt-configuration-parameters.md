# Windows XP 的 TCP/IP 和 NBT 配置参数

本文定义用于配置协议驱动程序的所有注册表参数，Tcpip.sys。 Tcpip.sys实现标准 TCP/IP 网络协议。

*适用于：* Windows XP  
*原始 KB 数：* 314053

## 简介

Windows XP 的 TCP/IP 协议套件实现从注册表读取其所有配置数据。 此信息由网络工具在安装过程中控制面板写入注册表。 如果启用了 DHCP 客户端服务，则动态主机配置协议 （DHCP） 客户端服务也提供了其中一些信息。

协议套件的实现应仅在大多数环境中正确高效地执行，方法是仅使用 DHCP 收集的配置信息以及控制面板中的网络工具收集的配置信息。 协议所有其他可配置方面的最佳默认值已在驱动程序中编码。

客户安装中可能存在一些不寻常的情况，其中某些默认值的更改是适当的。 若要处理这些情况，可以创建可选注册表参数以修改协议驱动程序的某些部分的默认行为。

注意

Windows XP TCP/IP 实现基本上是自我优化。 在不仔细研究的情况下调整注册表参数可能会降低计算机的性能。

## 如何更改参数

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 但是，注册表修改不当可能会出现严重问题。 因此，按以下步骤操作时请务必谨慎。 作为额外保护措施，请在修改注册表之前先将其备份。 如果之后出现问题，您就可以还原注册表。 有关如何备份和还原注册表的详细信息，请参阅：[如何备份和还原 Windows 中的注册表](https://support.microsoft.com/help/322756)。

若要更改这些参数，请执行以下步骤：

1. 单击“开始”，单击“运行**”**，然后在*“打开**”框中键入 regedit***。
2. 找到以下注册表项：  
   `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services`
3. 单击“**编辑**”菜单上的**“添加值**”，键入所需的值，然后在“数据类型**”下**设置值类型。
4. 单击“确定”。
5. 退出注册表编辑器。
6. 重新启动计算机以使更改生效。

所有 TCP/IP 参数都是位于以下两个不同子项之 `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services`一下的注册表值：

- `Tcpip\Parameters`
- `Tcpip\Parameters\Interfaces\ID for Adapter`

注意

**适配器** 的 ID 是 TCP/IP 绑定到的网络适配器。 若要确定适配器 ID 与网络连接之间的关系，请查看 `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Network\{4D36E972-E325-11CE-BFC1-08002BE10318}\<ID for Adapter>\Connection`。 这些键中的 Name 值为网络连接提供在“网络连接”文件夹中使用的友好名称。 这些键下的值特定于每个适配器。 具有 DHCP 配置值和静态配置值的参数可能或可能不存在。 它们的存在取决于计算机还是适配器是 DHCP 配置的，还是指定静态替代值。 必须重新启动计算机才能进行更改才能生效。

## 可以使用注册表编辑器配置的标准 TCP/IP 参数

在安装 TCP/IP 组件的过程中，网络工具在控制面板中安装了以下参数。 可以使用注册表编辑器对其进行修改。

- DatabasePath

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_EXPAND\_SZ - 字符串
  - 有效范围：有效的 Windows NT 文件路径
  - 默认值：%SystemRoot%\System32\Drivers\Etc
  - 说明：此参数指定标准 Internet 数据库文件的路径（HOSTS、LMHOSTS、NETWORKS、PROTOCOLS）。 Windows 套接字接口使用它。
- ForwardBroadcasts

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0 或 1 （False 或 True）
  - 默认值：0（False）
  - 说明：不支持转播。 忽略此参数。
- UseZeroBroadcast

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0 或 1 （False 或 True）
  - 默认值：0（False）
  - 说明：如果此参数设置为 1（True），IP 将使用零广播（0.0.0.0.0），而不是 ones-broadcasts（255.255.255.255.255）。 大多数计算机使用 ones-broadcast，但从 BSD 实现派生的某些计算机使用零广播。 使用不同广播的计算机不能在同一网络上很好地互操作。

## 可以使用注册表编辑器配置的可选 TCP/IP 参数

通常，注册表中不存在这些参数。 可以创建它们以修改 TCP/IP 协议驱动程序的默认行为。

- ArpAlwaysSourceRoute

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0,1 （False 或 True）
  - 默认值：0（False）
  - 说明：如果将此参数设置为 1，TCP/IP 会传输在令牌环网络上启用源路由的 ARP 查询。 默认情况下，堆栈先传输没有源路由的 ARP 查询，并在未收到回复时重试启用了源路由。
- ArpUseEtherSNAP

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0,1 （False 或 True）
  - 默认值：0（False）
  - 说明：如果将此参数设置为 1，TCP/IP 将使用 802.3 SNAP 编码传输以太网数据包。 默认情况下，堆栈以 DIX 以太网格式传输数据包。 它将始终接收这两种格式。
- DefaultTTL

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 秒/跃点数
  - 有效范围：1-255
  - 默认值：128 for Windows XP
  - 说明：此参数指定在传出 IP 数据包的标头中设置的默认生存时间（TTL）值。 TTL 确定 IP 数据包可以在网络中生存的最大时间，而无需到达其目标。 它实际上限制了 IP 数据包在丢弃之前可以传递的路由器数。
- EnableDeadGWDetect

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0,1 （假，真）
  - 默认值：1（True）
  - 说明：如果将此参数设置为 1，TCP 将使用死网关检测功能。 使用此功能，TCP 请求 IP 更改为备份网关（如果它多次重新传输段而不接收响应）。 可以在网络控制面板的 TCP/IP 配置**对话框的**“高级**”部分中定义**备份网关。
- EnablePMTUBHDetect

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0,1 （假，真）
  - 默认值：0（False）
  - 说明：如果将此参数设置为 1（True），TCP 会在执行路径 MTU 发现时尝试检测“黑洞”路由器。 当“黑洞”路由器必须分段未设置“片段位”的 IP 数据报时，它不会返回 ICMP 目标不可访问的消息。 TCP 必须接收这些消息才能执行路径 MTU 发现。 启用此功能后，如果未确认某个段的多个重新传输，TCP 将尝试发送未设置“不片段位”的段。 如果确认段，MSS 将减少，并且不会分段位将在连接的未来数据包中设置。 启用黑洞检测会增加为特定段执行的重新传输的最大数量。
- EnablePMTUDiscovery

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0,1 （假，真）
  - 默认值：1（True）
  - 说明：如果将此参数设置为 1（True），TCP 会尝试在远程主机的路径上发现最大传输单元（MTU 或最大数据包大小）。 通过发现路径 MTU 并将 TCP 段限制为此大小，TCP 可以消除路径上的路由器碎片，从而连接具有不同 MTU 的网络。 碎片对 TCP 吞吐量产生不利影响，并导致网络拥塞。 如果将此参数设置为 0，则 576 字节的 MTU 用于本地子网上计算机的所有连接。
- ForwardBufferMemory

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 字节数
  - 有效范围：网络 MTU - 小于0xFFFFFFFF的合理值
  - 默认值：74240（足以 50 个 1480 字节数据包，舍入为 256 的倍数）
  - 说明：此参数确定在路由器数据包队列中存储数据包数据的内存 IP 分配量。 当填充此缓冲区空间时，路由器将开始从其队列中随机丢弃数据包。 数据包队列数据缓冲区的长度为 256 字节。 因此，此参数的值必须是 256 的倍数。 对于较大的数据包，多个缓冲区一起链接在一起。 数据包的 IP 标头单独存储。 忽略此参数，如果未启用 IP 路由器，则不会分配任何缓冲区。
- IGMPLevel

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 数字
  - 有效范围：0,1,2
  - 默认值：2
  - 说明：此参数确定计算机如何支持 IP 多播并参与 Internet 组管理协议。 在级别 0 中，计算机不提供多播支持。 在级别 1 中，计算机只能发送 IP 多播数据包。 在级别 2 中，计算机可以发送 IP 多播数据包并完全参与 IGMP 来接收多播数据包。
- KeepAliveInterval

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 以毫秒为单位的时间
  - 有效范围：1 - 0xFFFFFFFF
  - 默认值：1000（一秒）
  - 说明：此参数确定在收到响应之前分隔保持性重新传输的间隔。 收到响应后，KeepAliveTime 再次控制延迟，直到下一次保持传输。 连接在 TcpMaxDataRetransmissions 指定的重新传输数未完成之后中止。
- KeepAliveTime

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 以毫秒为单位的时间
  - 有效范围：1 - 0xFFFFFFFF
  - 默认值：7,200,000 （两小时）
  - 说明：参数通过发送保持数据包来控制 TCP 尝试验证空闲连接是否仍然完好无损的频率。 如果远程计算机仍然可访问且正常运行，远程计算机将确认保持传输。 默认情况下，不发送保留数据包。 程序可以在连接上打开此功能。
- MTU

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_DWORD数字
  - 有效范围：68 - 基础网络的 MTU
  - 默认值：0xFFFFFFFF
  - 说明：此参数替代网络接口的默认最大传输单元（MTU）。 MTU 是传输通过基础网络传输的最大数据包大小（以字节为单位）。 大小包括传输标头。 IP 数据报可以跨越多个数据包。 大于基础网络的默认值的值会导致传输使用网络默认 MTU。 小于 68 的值会导致传输使用 68 的 MTU。
- NumForwardPackets

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD数字
  - 有效范围：1 - 小于0xFFFFFFFF的合理值
  - 默认值：50
  - 说明：此参数确定为路由器数据包队列分配的 IP 数据包标头数。 当所有标头都正在使用时，路由器开始从队列中随机丢弃数据包。 此值应至少与 ForwardBufferMemory 值一样大，除以连接到路由器的网络的最大 IP 数据大小。 此值不能大于除以 256 的 ForwardBufferMemory 值，因为每个数据包至少使用了 256 字节的转发缓冲区内存。 特定 ForwardBufferMemory 大小的最佳转发数据包数取决于网络上的流量类型，并将位于这两个值之间的某个位置。 忽略此参数，如果未启用路由器，则不会分配任何标头。
- TcpMaxConnectRetransmissions

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 数字
  - 有效范围：0 - 0xFFFFFFFF
  - 默认值：2
  - 说明：此参数确定 TCP 在中止尝试之前重新传输连接请求（SYN）的次数。 重新传输超时在特定的连接尝试中，每次连续重新传输都会增加一倍。 初始超时值为 3 秒。
- TcpMaxDataRetransmissions

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 数字
  - 有效范围：0 - 0xFFFFFFFF
  - 默认：5
  - 说明：此参数控制 TCP 在中止连接之前重新传输单个数据段（非连接段）的次数。 重新传输超时将加倍，连接上的每个连续重新传输。 响应恢复时会重置。 基本超时值由连接的测量往返时间动态确定。
- TcpNumConnections

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 数字
  - 有效范围：0 - 0xfffffe
  - 默认值：0xfffffe
  - 说明：此参数限制 TCP 可以同时打开的最大连接数。
- TcpTimedWaitDelay

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 以秒为单位的时间
  - 有效范围：30-300（小数）
  - 默认值：0x78（120 个小数）
  - 说明：此参数确定连接在关闭时保持TIME\_WAIT状态的时间。 只要连接处于TIME\_WAIT状态，就不能重新使用套接字对。 这也称为“2MSL”状态。 根据 RFC793，该值应是网络上的最大段生存期的两倍。 有关详细信息，请参阅 RFC793。

    注意

    Microsoft Windows 2000 中，默认值为 240 秒。 对于 Windows XP 和 Microsoft Windows Server 2003，IPv4 堆栈的默认更改为 120 秒以提高性能。 IPv6 堆栈的默认值为 240 秒。
- TcpUseRFC1122UrgentPointer

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0,1 （假，真）
  - 默认值：0（False）
  - 说明：此参数确定 TCP 是对紧急数据使用 RFC 1122 规范还是 BSD 派生计算机使用的模式。 这两种机制以不同的方式解释 TCP 标头中的紧急指针和紧急数据的长度。 它们不可互操作。 默认情况下，Windows XP 使用 BSD 模式。
- TcpWindowSize

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 字节数
  - 有效范围：0 - 0xFFFF
  - 默认值：较小的0xFFFF或大于网络 OR 8192 上的最大 TCP 数据大小四倍，舍入为网络 TCP 数据大小的偶数倍。
  - 以太网默认值：8760
  - 说明：此参数确定计算机的最大 TCP 接收窗口大小。 接收窗口指定发送方可以在不接收确认的情况下传输的字节数。 通常，较大的接收窗口可提高高（延迟 \* 带宽）网络的性能。 为了提高效率，接收窗口必须是 TCP 最大段大小（MSS）的偶数倍。

## 可从网络连接的属性配置的 TCP/IP 参数

以下参数通过用户提供的信息由连接属性接口自动创建和修改。 无需直接在注册表中配置它们。

- DefaultGateway

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_MULTI\_SZ - 点小数 IP 地址列表
  - 有效范围：任意一组有效的 IP 地址
  - 默认值：无
  - 说明：此参数指定网关列表，用于路由未发往计算机直接连接的子网且没有更具体路由的子网的数据包。 此参数替代 DhcpDefaultGateway 参数。
- Domain

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_SZ - 字符串
  - 有效范围：任何有效的 DNS 域名
  - 默认值：无
  - 说明：此参数指定计算机的 DNS 域名。 Windows 套接字接口使用它。
- EnableDhcp

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0 或 1 （False 或 True）
  - 默认值：0（False）
  - 说明：如果此参数设置为 1（True），DHCP 客户端服务将尝试使用 DHCP 在适配器上配置第一个 IP 接口。
- 主机名

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_SZ - 字符串
  - 有效范围：任何有效的 DNS 主机名
  - 默认值：计算机的计算机名称
  - 说明：此参数指定主机名命令将返回的计算机的 DNS 主机名。
- IPAddress

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_MULTI\_SZ - dotted-decimal IP 地址列表
  - 有效范围：任意一组有效的 IP 地址
  - 默认值：无
  - 说明：此参数指定要绑定到适配器的 IP 接口的 IP 地址。 如果列表中的第一个地址为 0.0.0.0，则适配器上的主接口将从 DHCP 进行配置。 适配器具有多个 IP 接口的计算机称为“逻辑上多宿主”。对于此参数中指定的每个 IP 地址，SubnetMask 参数中必须有一个有效的子网掩码值。
- IPEnableRouter

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0 或 1 （False 或 True）
  - 默认值：0（False）
  - 说明：将此参数设置为 1（True）会导致计算机在连接到的网络之间路由 IP 数据包。
- NameServer

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_SZ - 以空格分隔的十进制 IP 地址列表
  - 有效范围：任意一组有效的 IP 地址
  - 默认值：无（空白）
  - 说明：此参数指定要由 Windows 套接字查询的 DNS 名称服务器来解析名称。
- SearchList

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_SZ - DNS 域名后缀的分隔列表
  - 有效范围：任意一组有效的 DNS 域名后缀
  - 默认值：无
  - 说明：此参数指定域名后缀列表，以追加到 DNS 解析的域名后缀列表（如果解析未修复的名称失败）。 默认情况下，域参数的值仅追加。 此参数由 Windows 套接字接口使用。
- SubnetMask

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_MULTI\_SZ - 点小数 IP 地址列表
  - 有效范围：任何有效的 IP 地址集。
  - 默认值：无
  - 说明：此参数指定要与绑定到适配器的 IP 接口一起使用的子网掩码。 如果列表中的第一个掩码为 0.0.0.0，则适配器上的主接口将由 DHCP 配置。 对于 IPAddress 参数中指定的每个 IP 地址，此参数中必须有一个有效的子网掩码值。

## 不可配置的 TCP/IP 参数

TCP/IP 组件在内部创建和使用以下参数。 不应使用注册表编辑器修改它们。 此处仅列出了它们以供参考。

- DhcpDefaultGateway

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_MULTI\_SZ - 点小数 IP 地址列表
  - 有效范围：任意一组有效的 IP 地址
  - 默认值：无
  - 说明：此参数指定默认网关列表，以路由未发往计算机直接连接到的子网且没有更具体路由的子网的数据包。 如果已启用，则此参数由 DHCP 客户端服务编写。 此参数由有效的 DefaultGateway 参数值重写。
- DhcpIPAddress

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_SZ - 点状十进制 IP 地址
  - 有效范围：任何有效的 IP 地址
  - 默认值：无
  - 说明：此参数指定接口的 DHCP 配置的 IP 地址。 如果 IPAddress 参数包含除 0.0.0.0 以外的第一个值，该值将替代此参数。
- DhcpNameServer

  - 键：`Tcpip\Parameters`
  - 值类型：REG\_SZ - 以空格分隔的十进制 IP 地址列表
  - 有效范围：任意一组有效的 IP 地址
  - 默认值：无
  - 说明：此参数指定要由 Windows 套接字查询的 DNS 名称服务器来解析名称。 它由 DHCP 客户端服务（如果已启用）编写。 NameServer 参数将替代此参数。
- DhcpServer

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_SZ - 点状十进制 IP 地址
  - 有效范围：任何有效的 IP 地址
  - 默认值：无
  - 说明：此参数指定 DHCP 服务器的 IP 地址，该地址授予 DhcpIPAddress 参数中 IP 地址的租约。
- DhcpSubnetMask

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_SZ - 点状十进制 IP 子网掩码
  - 有效范围：任何对配置的 IP 地址有效的子网掩码
  - 默认值：无
  - 说明：此参数为 DhcpIPAddress 参数中指定的地址指定 DHCP 配置的子网掩码。
- IPInterfaceContext

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_DWORD
  - 有效范围：0 - 0xFFFFFFFF
  - 默认值：无
  - 说明：此参数由 TCP/IP 驱动程序编写，供 DHCP 客户端服务使用。
- Lease

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_DWORD - 以秒为单位的时间
  - 有效范围：1 - 0xFFFFFFFF
  - 默认值：无
  - 说明：DHCP 客户端服务使用此参数来存储此适配器 IP 地址上的租约有效时间（以秒为单位）。
- LeaseObtainedTime

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_DWORD - 自 1/1/70 午夜以来的绝对时间（以秒为单位）
  - 有效范围：1 - 0xFFFFFFFF
  - 默认值：无
  - 说明：DHCP 客户端服务使用此参数来存储获取此适配器的 IP 地址租约的时间。
- LeaseTerminatesTime

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_DWORD - 自 1/1/70 午夜以来的绝对时间（以秒为单位）
  - 有效范围：1 - 0xFFFFFFFF
  - 默认值：无
  - 说明：DHCP 客户端服务使用此参数来存储此适配器的 IP 地址租约过期的时间。
- LLInterface

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_SZ - NT 设备名称
  - 有效范围：有效的 NT 设备名称
  - 默认值：空字符串（空白）
  - 说明：此参数用于定向 IP 以绑定到与内置 ARP 模块不同的链接层协议。 参数的值是 IP 应绑定到的基于 Windows NT 的设备的名称。 例如，此参数与 RAS 组件结合使用。
- T1

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_DWORD - 自 1/1/70 午夜以来的绝对时间（以秒为单位）
  - 有效范围：1 - 0xFFFFFFFF
  - 默认值：无
  - 说明：DHCP 客户端服务使用此参数来存储服务首次尝试在适配器的 IP 地址上续订租约的时间。 若要续订租约，他服务会联系授予租约的服务器。
- T2

  - 键：`Tcpip\Parameters\Interfaces\ID for Adapter`
  - 值类型：REG\_DWORD - 自 1/1/70 午夜以来的绝对时间（以秒为单位）
  - 有效范围：1 - 0xFFFFFFFF
  - 默认值：无
  - 说明：DHCP 客户端服务使用此参数来存储服务尝试续订适配器 IP 地址上的租约的时间。 若要续订租约，服务会广播续订请求。 仅当服务无法与原始服务器续订租约时，才应达到 T2 的时间。

所有 NBT 参数都是位于以下两个不同子项之 `HKEY_LOCAL_MACHINE\computer\CurrentControlSet\Services`一下的注册表值：

- `Netbt\Parameters`
- `Netbt\Parameters\Interfaces\Tcpip_ID for Adapter`

其中 **，适配器** 的 ID 表示 NBT 绑定到的网络适配器。 适配器 ID 与网络连接之间的关系可以通过检查 `HKEY_LOCAL_MACHINE\computer\CurrentControlSet\Control\Network\{4D36E972-E325-11CE-BFC1-08002BE10318}\ID for Adapter\Connection`来确定。 这些键中的“名称”值提供用于“网络连接”文件夹中使用的网络连接的名称。 后一个键下的值特定于每个适配器。 如果计算机是通过 DHCP 配置的，则如果命令在命令行界面中发出命令 `ipconfig /renew` ，参数中的更改将生效。 否则，必须重新启动计算机，才能更改其中任何参数才能生效。

## 可从注册表编辑器配置的标准 NBT 参数

在安装 TCP/IP 组件的过程中，网络工具在控制面板中安装了以下参数。 可以使用注册表编辑器（Regedit.exe）修改它们。

- BcastNameQueryCount

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 计数
  - 有效范围：1 到 0xFFFF
  - 默认值：3
  - 说明：此值确定 NetBT 在不接收响应的情况下广播特定名称的查询的次数。
- BcastQueryTimeout

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 以毫秒为单位的时间
  - 有效范围：100 到 0xFFFFFFFF
  - 默认值：0x2ee（750 十进制）
  - 说明：此值确定相同名称的连续广播名称查询之间的时间间隔。
- CacheTimeout

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 以毫秒为单位的时间
  - 有效范围：60000 到0xFFFFFFFF
  - 默认值：0x927c0（600000 毫秒 = 10 分钟）
  - 说明：此值确定在远程名称表中缓存名称的时间间隔。
- NameServerPort

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - UDP 端口号
  - 有效范围：0 - 0xFFFF
  - 默认值：0x89
  - 说明：此参数确定 NetBT 将数据包发送到与名称服务相关的目标端口号，例如名称查询和将名称注册发送到 WINS。 Microsoft WINS 侦听端口0x89。 来自其他供应商的 NetBIOS 名称服务器可以侦听不同的端口。
- NameSrvQueryCount

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 计数
  - 有效范围：0 - 0xFFFF
  - 默认值：3
  - 说明：此值确定 NetBT 为指定名称向 WINS 服务器发送查询的次数，而无需接收响应。
- NameSrvQueryTimeout

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 以毫秒为单位的时间
  - 有效范围：100 - 0xFFFFFFFF
  - 默认值：1500 （1.5 秒）
  - 说明：此值确定特定名称的连续名称查询到 WINS 之间的时间间隔。
- SessionKeepAlive

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 以毫秒为单位的时间
  - 有效范围：60,000 - 0xFFFFFFFF
  - 默认值：3,600,000 （1 小时）
  - 说明：此值确定会话上保持传输之间的时间间隔。 将值设置为0xFFFFFFF禁用 keepalives。
- 大小/小/中/大

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD
  - 有效范围：1、2、3 （小、中、大）
  - 默认值：1 （小型）
  - 说明：此值确定用于存储本地和远程名称的名称表的大小。 一般来说，Small 已经足够了。 如果计算机充当代理名称服务器，则该值会自动设置为“大”，以增加名称缓存哈希表的大小。 哈希表存储桶的大小如下：大：256 中型：128 小：16

## 可从注册表编辑器配置的可选 NBT 参数

注册表中通常不存在这些参数。 可以创建它们以修改 NetBT 协议驱动程序的默认行为。

- BroadcastAddress

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 四个字节，小字节编码的 IP 地址
  - 有效范围：0 - 0xFFFFFFFF
  - 默认值：每个网络的 ones-broadcast 地址。
  - 说明：此参数可用于强制 NetBT 对所有广播名称相关的数据包使用特定地址。 默认情况下，NetBT 使用适用于每个网络（即，对于子网掩码为 255.255.0.0 的网络，子网广播地址为 11.101.255.255.255）。 例如，如果网络使用零广播地址（使用 UseZeroBroadcast TCP/IP 参数设置），则会设置此参数。 然后，在前面的示例中，相应的子网广播地址将为 11.101.0.0。 然后，此参数将设置为0x0b650000。 此参数是全局的，用于 NetBT 绑定到的所有子网。
- EnableProxy

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0 或 1 （False 或 True）
  - 默认值：0（False）
  - 说明：如果此值设置为 1（True），则计算机充当 NBT 绑定到的网络的代理服务器。 代理服务器回答通过 WINS 解析的名称广播查询。 使用代理服务器时，B 节点实现的网络可以连接到已注册到 WINS 的其他子网上的服务器。
- EnableProxyRegCheck

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0 或 1 （False 或 True）
  - 默认值：0（False）
  - 说明：如果此参数设置为 1（True），则如果名称已注册到 WINS 或位于具有不同 IP 地址的代理本地名称缓存中，则代理名称服务器会向广播名称注册发送负响应。 启用此功能的危害在于，只要 WINS 具有名称的映射，计算机就无法更改其 IP 地址。 因此，它默认处于禁用状态。
- InitialRefreshT.O.

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 以毫秒为单位的时间
  - 有效范围：960000 - 0xFFFFFFF
  - 默认值：960000 （16 分钟）
  - 说明：此参数指定 NBT 在名称注册期间使用的初始更新超时。 NBT 尝试在此时间间隔的第一次注册名称时，以 1/8 的时间间隔联系 WINS 服务器。 当它收到成功的注册响应时，该响应包含要使用的新更新间隔。
- LmhostsTimeout

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 以毫秒为单位的时间
  - 有效范围：1000 - 0xFFFFFFFF
  - 默认值：6000 （6 秒）
  - 说明：此参数指定 LMHOSTS 和 DNS 名称查询的超时值。 计时器的超时值粒度。 因此，实际超时值可能高达两倍。
- MaxDgramBuffering

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 字节计数
  - 有效范围：0 - 0xFFFFFFFF
  - 默认值：0x20000（128 Kb）
  - 说明：此参数指定 NetBT 为所有未完成的数据报发送动态分配的最大内存。 达到此限制后，由于可用资源不足，因此其他发送将失败。
- NodeType

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 数字
  - 有效范围：1,2,4,8（B 节点、P 节点、M-node、H-node）
  - 默认值：1 或 8 基于 WINS 服务器配置
  - 说明：此参数确定 NetBT 用于注册和解析名称的方法。 B 节点计算机使用广播。 P 节点计算机仅对名称服务器使用点到点名称查询（WINS）。 M 节点计算机首先广播，然后查询名称服务器。 H 节点计算机先查询名称服务器，然后广播。 通过 LMHOSTS 或 DNS 解析遵循这些方法。 如果存在此密钥，它将替代 DhcpNodeType 密钥。 如果两个密钥都不存在，则计算机使用 B 节点（如果没有为网络配置的 WINS 服务器）。 如果至少配置了一个 WINS 服务器，计算机将使用 H 节点。
- RandomAdapter

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0 或 1 （False 或 True）
  - 默认值：0（False）
  - 说明：此参数仅适用于多宿主主机。 如果设置为 1（True），NetBT 会随机选择 IP 地址，以从其所有绑定接口放入名称查询响应中。 通常，响应包含查询到达的接口的地址。 此功能将由在同一网络上具有两个接口的服务器使用，以便进行负载均衡。
- RefreshOpCode

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 数字
  - 有效范围：8、9
  - 默认值：8
  - 说明：此参数强制 NetBT 在名称更新数据包中使用特定的操作码。 在此区域中，NetBT 协议的规范有些模糊。 尽管Microsoft实现使用的默认值为 8，但其他一些实现（例如 Ungermann-Bass 使用的实现）使用值 9。 两个实现必须使用相同的操作代码进行互操作。
- SingleResponse

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0 或 1 （False 或 True）
  - 默认值：0（False）
  - 说明：此参数仅适用于多宿主主机。 如果此参数设置为 1（True），NBT 只会在名称查询响应中从其绑定接口之一提供 IP 地址。 默认情况下，包括所有绑定接口的地址。
- WinsDownTimeout

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 以毫秒为单位的时间
  - 有效范围：1000 - 0xFFFFFFFF
  - 默认值：15,000 （15 秒）
  - 说明：此参数确定 NBT 在未联系任何 WINS 服务器后再次尝试使用 WINS 的时间。 借助此功能，暂时断开网络连接的计算机可以继续启动处理，而无需等待超时每个 WINS 名称注册或单独查询。

## 可从连接属性配置的 NBT 参数

可以通过“网络连接”文件夹中的连接属性设置以下参数。 无需直接配置它们。

- EnableDns

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0 或 1 （False 或 True）
  - 默认值：0（False）
  - 说明：如果此值设置为 1（True），NBT 将查询 DNS 以获取 WINS、广播或 LMHOSTS 文件无法解析的名称。
- EnableLmhosts

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 布尔值
  - 有效范围：0 或 1 （False 或 True）
  - 默认值：1（True）
  - 说明：如果此值设置为 1（True），NBT 将搜索 LMHOSTS 文件（如果存在），以获取 WINS 或广播无法解析的名称。 默认情况下，没有 LMHOSTS 文件数据库目录（由指定）。`Tcpip\Parameters\DatabasePath` 因此，NBT 不采取任何操作。 此值由 控制面板 中的网络工具下的高级 TCP/IP 配置编写。
- NameServer

  - 键：`Netbt\Parameters\Interfaces\Tcpip_ID for Adapter`
  - 值类型：REG\_SZ - 点化十进制 IP 地址（例如，11.101.1.200）
  - 有效范围：任何有效的 IP 地址
  - 默认值：空白（无地址）
  - 说明：此参数指定主 WINS 服务器的 IP 地址。 如果此参数包含有效值，则会重写同名的 DHCP 参数。
- NameServerBackup

  - 键：`Netbt\Parameters\Interfaces\Tcpip_ID for Adapter`
  - 值类型：REG\_SZ - 点状十进制 IP 地址（例如 11.101.1.200）
  - 有效范围：任何有效的 IP 地址。
  - 默认值：空白（无地址）
  - 说明：此参数指定备份 WINS 服务器的 IP 地址。 如果此参数包含有效值，则会重写同名的 DHCP 参数。
- ScopeId

  - 键：`Netbt\Parameters`
  - 值类型：REG\_SZ - 字符串
  - 有效范围：由两个点分隔部分或“\*”组成的任何有效的 DNS 域名。
  - 默认值：无
  - 说明：此参数指定节点的 NetBIOS 名称范围。 此值不得以句点开头。 如果此参数包含有效值，它将重写同名的 DHCP 参数。 将忽略空值（空字符串）。 将此参数设置为值“\*”表示 null 范围，并将替代 DHCP 参数。

## 不可配置的 NBT 参数

NetBT 组件在内部创建和使用以下参数。 不应使用注册表编辑器修改它们。 此处仅列出了它们以供参考。

- DhcpNameServer

  - 键：`Netbt\Parameters\Interfaces\Tcpip_ID for Adapter`
  - 值类型：REG\_SZ - 点状十进制 IP 地址（例如 11.101.1.200）
  - 有效范围：任何有效的 IP 地址
  - 默认值：无
  - 说明：此参数指定主 WINS 服务器的 IP 地址。 它由 DHCP 客户端服务（如果已启用）编写。 有效的 NameServer 值将替代此参数。
- DhcpNameServerBackup

  - 键：`Netbt\Parameters\Interfaces\Tcpip_ID for Adapter`
  - 值类型：REG\_SZ - 点状十进制 IP 地址（例如 11.101.1.200）
  - 有效范围：任何有效的 IP 地址
  - 默认值：无
  - 说明：此参数指定备份 WINS 服务器的 IP 地址。 它由 DHCP 客户端服务（如果已启用）编写。 有效的 BackupNameServer 值将替代此参数。
- DhcpNodeType

  - 键：`Netbt\Parameters`
  - 值类型：REG\_DWORD - 数字
  - 有效范围：1 - 8
  - 默认值：1
  - 说明：此参数指定 NBT 节点类型。 它由 DHCP 客户端服务（如果已启用）编写。 有效的 NodeType 值将替代此参数。 有关完整说明，请参阅 NodeType 的条目。
- DhcpScopeId

  - 键：`Netbt\Parameters`
  - 值类型：REG\_SZ - 字符串
  - 有效范围：点分隔的名称字符串，例如 `microsoft.com`
  - 默认值：无
  - 说明：此参数指定节点的 NetBIOS 名称范围。 它由 DHCP 客户端服务（如果已启用）编写。 此值不得以句点开头。 有关详细信息，请参阅 ScopeId 条目。
- NbProvider

  - 键：`Netbt\Parameters`
  - 值类型：REG\_SZ - 字符串
  - 有效范围：\_tcp
  - 默认值：\_tcp
  - 说明：RPC 组件在内部使用此参数。 不应更改默认值。
- TransportBindName

  - 键：`Netbt\Parameters`
  - 值类型：REG\_SZ - 字符串
  - 有效范围：N/A
  - 默认值：\Device\
  - 说明：此参数在产品开发期间在内部使用。 不应更改默认值。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/tcpip-and-nbt-configuration-parameters)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
