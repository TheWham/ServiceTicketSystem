# 已加入域的计算机无法检测到域配置文件

本指南可帮助排查已加入域的计算机无法检测到域配置文件的情况。

计算机已加入域网络，但无法检测此网络的域配置文件，你可能会注意到以下问题或症状：

- 网络状态在系统托盘中显示为“未识别的网络”。
- 计算机上应用了不正确的防火墙配置文件。 例如，即使计算机已加入域，也会应用公共配置文件。
- 不会应用在域配置文件下配置的防火墙规则，从而导致连接问题。
- 与内部应用程序的连接可能会失败，因为域配置文件未处于活动状态。

## 网络位置感知概述 （NLA）

网络位置感知（NLA）服务对以下任何网络更改执行网络位置检测：

- 添加或删除任何 IP 路由。
- 添加或删除任何 IP 地址。
- 断开或重新连接网络适配器。
- 禁用或重新启用网络适配器。
- 动态主机配置协议 （DHCP） 事件 （租用续订， 域名系统 （DNS） 服务器添加或删除， 等等。
- 对网络连接状态指示器（NCSI）设置的任何更改，例如 [DomainLocationDeterminationUrl](https://gpsearch.azurewebsites.net/Default.aspx?PolicyID=2583#1993) 设置。

## NLA 的域身份验证

当已加入域的计算机连接到新网络时，它会执行以下检查，以确定它是否在域网络中。 NCSI 确定 Internet 连接，NLA 对网络配置文件执行域身份验证。

任何网络更改都触发 NCSI 检测，NLA 会尝试向域控制器（DC）进行身份验证，以将正确的配置文件分配给 Windows 防火墙。

下面是身份验证步骤：

1. NLA 服务调用 `DsGetDcName` 函数以检索 DC 名称。 这是通过 DNS 名称解析完成的，例如 `_ldap._tcp.<SiteName>._sites.dc._msdcs.<DomainName>`。
2. DNS 名称解析成功并返回 DC 名称后，在端口 389 上与在上一步中检索到的 DC 建立轻型目录访问协议（LDAP）连接。
3. 计算机通过 TCP 端口 389 与 DC 建立 TCP 连接，并发送 LDAP 绑定请求。 此 LDAP 绑定成功后，计算机将在域网络中标识自身。

根据域检测过程是否成功，将相应地应用防火墙配置文件。

运行 Windows 7、Windows Server 2008 R2 及更高版本的操作系统的计算机可以检测以下网络位置类型：

- 公用

  默认情况下，当计算机首次连接时，公共网络位置类型将分配给任何新网络。 公共配置文件用于指定公共网络，例如咖啡店、机场和其他位置的 Wi-Fi 热点。
- 专用

  本地管理员可以手动选择专用网络位置类型，以便连接到无法直接访问公众的网络。 此连接可以通过使用防火墙设备或执行网络地址转换（NAT）的设备链接到与可公开访问的网络隔离的家庭或办公室网络。
- Domain

  当本地计算机是 Active Directory 域的成员时，将检测到域网络位置类型，本地计算机可以通过其中一个网络连接向该域的 DC 进行身份验证。 管理员无法手动分配此网络位置类型。

将多个网络适配器附加到计算机时，可以连接到不同类型的网络。 运行 Windows 7、Windows Server 2008 R2 及更高版本的操作系统的计算机支持不同的网络位置类型。

NLA 服务的功能是收集和存储网络的配置信息，并在修改该信息时通知程序。

NLA 收集的信息由网络列表服务 （NLS） 服务策划，并存储在该服务下 `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkList`。

从 Windows 11 开始，NLA 服务不再负责检测域配置文件。 相反，网络列表管理器会执行此作业，并在系统上下文中运行。

下面是一些重要的注册表，可帮助诊断当前配置文件、网络或适配器状态：

| 位置 | 使用情况 |
| --- | --- |
| `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkList\Signatures\Managed` | 此注册表项显示存储在 Windows 注册表中的托管网络配置文件。 |
| `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkList\Signatures\Unmanaged` | 此注册表项显示存储在 Windows 注册表中的非托管网络配置文件。 |
| `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkList\Profiles\{985EE69C-23B4-4D38-AC66-5F0D6AD8A128}` | 此注册表项包含有关 Windows 中的网络配置文件和网络配置文件的当前类别的信息。  表示网络不是 Active Directory 网络的值 `0` 。  `1`这意味着网络是 Active Directory 网络，但此计算机未对其进行身份验证。  `2`这意味着网络是一个 Active Directory 网络，并且此计算机针对它进行身份验证。 |

## 检查当前应用的网络配置文件

可以使用以下 PowerShell cmdlet 验证已加入域的计算机是否可以成功检测域网络配置文件：

```
PS C:\Users\admin> Get-NetConnectionProfile
Name             : contoso.com
InterfaceAlias   : Contoso
InterfaceIndex   : 13
NetworkCategory  : DomainAuthenticated
IPv4Connectivity : Internet
IPv6Connectivity : NoTraffic
```

## 排查域检测问题

1. 通过解析名称 `_ldap._tcp.<SiteName>._sites.dc._msdcs.<DomainName>`，检查计算机是否可以标识 LDAP 服务器或 DC。

   在管理命令提示符或 PowerShell 窗口中运行以下命令以强制 DC 发现：

   ```
   Nltest /dsgetdc:<DomainName> /force
   ```

   确保可以在命令的输出中列出 DC 名称，例如：

   ```
   PS C:\tss> nltest /dsgetdc:contoso.com /force
              DC: \\DC.contoso.com
         Address: \\10.0.1.2
        Dom Guid: <GUID>
        Dom Name: contoso.com
     Forest Name: contoso.com
    Dc Site Name: Default-First-Site-Name
   Our Site Name: Default-First-Site-Name
           Flags: PDC GC DS LDAP KDC TIMESERV WRITABLE DNS_DC DNS_DOMAIN DNS_FOREST CLOSE_SITE FULL_SECRET WS DS_8 DS_9 DS_10 KEYLIST
   The command completed successfully
   ```

   如果 DNS 名称解析失败并返回 `DsGetDcName function Failed with ERROR_NO_SUCH_DOMAIN`，则计算机不会在域网络中标识自身，即使它位于企业网络内部也是如此。
2. 检查计算机是否可以与上一步中标识的 DC 建立 TCP 端口 389 连接。

   确保 Windows 防火墙中允许 TCP 端口 389。

   在管理命令提示符或 PowerShell 窗口中运行以下命令，检查与 DC 的 TCP 连接是否成功：

   ```
   Telnet <DCName or IP> 389
   ```

   如果打开空白窗口，则表示可以成功建立 TCP 连接。

   如果失败，NLA 域检测过程无法继续，计算机无法识别域网络。
3. 检查计算机是否可以在已建立的 TCP 端口 389 连接内与 DC 执行 LDAP 绑定。

   在 NLA 域检测过程中收集的网络跟踪中的 TCP 端口 389 会话中可以看到 LDAP 绑定请求和响应。

   如果 LDAP 绑定失败，ncpa.cpl的网络适配器上会显示“未经身份验证”。 它将显示为“Contoso.com（未经身份验证）。
4. 检查 Microsoft-Windows-NetworkProfile/Operational 事件日志中是否存在任何错误。

   下面是成功的域检测示例。

   正在进行的网络标识：

   ![事件日志的屏幕截图，其中显示了正在进行的网络标识。](media/domain-joined-machines-cannot-detect-domain-profile/network-identification-progress.png)

   标识的域网络：

   ![事件日志的屏幕截图，其中显示了标识的域网络。](media/domain-joined-machines-cannot-detect-domain-profile/domain-network-identified.png)

## 网络捕获分析

若要对方案进行故障排除，可以在禁用和重新启用网络适配器或重启 NLS 服务时使用 [Wireshark](https://www.wireshark.org/download.html) 收集网络捕获（这会触发 NLA 域检测过程）。

注意

在某些情况下，可以通过禁用并重新启用适配器或重启 NLS 服务来解决该问题。 只有在问题仍然存在时，才能收集网络跟踪。

若要下载 Wireshark，请参阅 [“下载 Wireshark](https://www.wireshark.org/download.html)”。

若要捕获 Wireshark 跟踪，请参阅“开始捕获[”中的](https://www.wireshark.org/docs/wsug_html_chunked/ChCapCapturingSection.html)步骤。

收集网络跟踪后，可以按照以下步骤执行基本分析以确定根本原因。

在 Wireshark 中打开网络捕获。 在“应用显示筛选器”空间中，键入 *dns* 并应用筛选器。

查找为名称“\_ldap”发送的 DNS 查询，以标识域中的 DC。

成功的名称解析应类似于以下示例：

```
292 <DateTime>  10.0.1.10   10.0.1.2    DNS 130         Standard query 0x9022 SRV _ldap._tcp.Default-First-Site-Name._sites.dc._msdcs.contoso.com
293 <DateTime>  10.0.1.2    10.0.1.10   DNS 173         Standard query response 0x9022 SRV _ldap._tcp.Default-First-Site-Name._sites.dc._msdcs.contoso.com SRV 0 100 389 dc.contoso.com A 10.0.1.2
```

下一步是通过 TCP 端口 389 成功建立 LDAP 连接，并将标识的 DC 标识为目标。

在显示筛选器空间中应用筛选器“ip.addr==10.0.1.2 和 tcp.port=389”来标识此 TCP 会话。

注意

筛选器中的值 `10.0.1.2` 需要替换为环境中获取的 DC 的 IP 地址。

成功的 LDAP 连接和绑定应如下所示：

建立 TCP 连接：

```
298 <DateTime>  10.0.1.10   10.0.1.2    TCP 66  1521521070  0   59506 → 389 [SYN, ECE, CWR] Seq=0 Win=64240 Len=0 MSS=1460 WS=256 SACK_PERM
299 <DateTime>  10.0.1.2    10.0.1.10   TCP 66  690649648   1521521071  389 → 59506 [SYN, ACK, ECE] Seq=0 Ack=1 Win=65535 Len=0 MSS=1460 WS=256 SACK_PERM
300 <DateTime>  10.0.1.10   10.0.1.2    TCP 54  1521521071  690649649   59506 → 389 [ACK] Seq=1 Ack=1 Win=2097920 Len=0
```

LDAP 绑定成功完成：

```
316 <DateTime>  10.0.1.10   10.0.1.2    LDAP    1912    1521521422  690652335   bindRequest(267) "<ROOT>" sasl 
318 <DateTime>  10.0.1.2    10.0.1.10   LDAP    266 690652335   1521523280  bindResponse(267) success
```

若要进一步进行故障排除，请联系Microsoft 支持部门。

## 数据收集

在联系Microsoft 支持部门之前，可以收集有关问题的信息。

使用 [TSS 工具集](../windows-tss/introduction-to-troubleshootingscript-toolset-tss)下载和收集日志，然后使用以下 cmdlet 在受影响的计算机上启用日志收集：

```
.\TSS.ps1 -Scenario NET_NCSI
```

**第三方信息免责声明**

本文中提到的第三方产品由 Microsoft 以外的其他公司提供。 Microsoft 不对这些产品的性能或可靠性提供任何明示或暗示性担保。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/domain-joined-machines-cannot-detect-domain-profile)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
