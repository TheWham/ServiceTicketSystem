# 用于最大程度地减少定期 WAN 流量的设置

本文提供了一些建议的设置，说明通过定期 WAN 流量激活按需拨号链接时出现的问题。

*原始 KB 数：* 819108

## 总结

本文介绍影响定期广域网（WAN）流量和按流量计费的链接成本的注册表设置和组策略设置。 如果有按需拨号链接，则定期 WAN 流量可能会意外地启用该链接。 可以配置系统的组件和服务，以最大程度地减少定期 WAN 流量并降低按流量计费的链接成本。

## 现象

如果满足以下条件，则当计算机处于空闲状态时，按需拨号链接将激活：

- 你使用的是Microsoft基于 Windows 的计算机，该计算机连接到远程网络，并且是 Active Directory 域服务 （AD DS） 域的成员。
- 通过按需拨号或其他按流量计费的链接连接到域控制器。

## 解决方法

以下部分包含注册表设置和组策略设置的综合摘要，可以添加或修改这些设置以最大程度地减少 WAN 流量。 其中一些设置取决于计算机正在运行的操作系统版本。

## 第 1 部分：相关设置的说明

以下注册表设置会影响 WAN 流量和按流量计费的链接成本。 若要最大程度地减少定期 WAN 流量并减少按流量计费的链接成本，请根据需要配置这些设置。

### 浏览器服务

在 Windows Server 2016、Windows 10 及更高版本中，浏览器服务通常不再使用。 如果可能，建议在企业中的所有计算机上禁用该服务。 如果无法执行此操作，建议关闭服务的通信间隔。

#### 域主浏览器周期性

主域控制器（PDC）始终是域主浏览器。 因此，当域尝试查找 PDC 时，未托管 PDC 的网络上的主浏览器会激活按需拨号链接。 默认情况下，尝试间隔为 5 分钟。 可以创建 MasterPeriodicity  注册表项，该条目指示 Browser 服务调整其与域主浏览器联系的默认间隔。 默认情况下， **MasterPeriodicity** 条目不存在。 按需拨号部署的建议默认值为 **86,400** 秒（一天）。

子项：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Browser\Parameters`  
条目：MasterPeriodicity  
类型：DWORD  
建议的值（秒）：86,400

#### 服务器列表维护

如果使服务器能够作为浏览器参与，并可能将其网络选为主浏览器，则服务器会定期联系 PDC 作为其域。 默认情况下， **MaintainServerList** 注册表项设置为 **“自动**”。除非必须在网络上具有浏览器功能，否则建议的值为 **“否** ”。 如果必须具有浏览器功能，请将此值设置为 **“是**”。 但是，请确保将 MasterPeriodicity **间隔配置为**足够大的间隔，以减少 PDC 联系人的数量。

子项：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Browser\Parameters`  
条目：MaintainServerList  
类型：字符串默认值：自动  
建议的值：否

#### 预期的拨号延迟

**ExpectedDialupDelay** 条目指定在将消息从客户端计算机发送到域时，拨号路由器在通过慢速链接将消息发送到域时需要的时间。 在此方案中，该域受客户端计算机信任。 通常，Net Logon 服务假定它可以快速到达域控制器。 通过设置 **ExpectedDialupDelay** 条目，可以通知 Net Logon 服务预期会出现额外的延迟。 此设置的建议值是建立按需拨号链接所需的平均时间（以秒为单位）以及用于考虑方差的常量 5 秒。

子项：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters`  
条目：ExpectedDialupDelay  
类型：DWORD  
建议的值（秒）：90

### AvoidPdcOnWan 条目

**AvoidPdcOnWan** 条目指示运行 Net Logon 服务的域控制器，以避免尽可能多地联系 PDC 操作主角色。 （操作主角色也称为灵活的单主操作角色或 FSMO 角色。 **AvoidPdcOnWan** 条目还会指示使用此信息的其他组件，例如安全帐户管理器（SAM）。 例如，假设在远程站点的域控制器上启用了此项。 在这种情况下，如果客户端未使用本地域控制器进行身份验证，远程域控制器将不会尝试使用 PDC 操作主角色验证密码。

子项：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters`  
条目：AvoidPdcOnWan  
类型：DWORD  
建议的值：1（已启用）

### 目录服务客户端查询

在 Windows 2000 Service Pack 2 和更高版本的 Windows 2000 Service Pack、Windows XP 和 Windows Server 2003 中，目录服务客户端查询每小时发出一次。 可以调整以下注册表项，以将此查询时间扩展到一小时之后。

#### 负缓存周期

**NegativeCachePeriod** 条目指定客户端在域中找不到域控制器的时间。 如果程序在此时间内再次尝试，则客户端调用会立即失败，而不会再次尝试查找域控制器，因此不会激活按流量计费的链接。

子项：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters`  
条目：NegativeCachePeriod  
类型：DWORD  
默认值（秒）：45  
建议的值：84,600

#### 后台重试初始周期

某些程序会定期尝试查找域控制器。 如果域控制器不可用，则这些定期重试在按需拨号方案中可能很昂贵。 **BackgroundRetryInitialPeriod** 条目定义首次重试前的最小运行时间。 如果该值小于 NegativeCachePeriod 条目中**设置的值，**则使用 NegativeCachePeriod**** 值。

子项：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters`  
条目：BackgroundRetryInitialPeriod  
类型：DWORD  
建议的值（秒）：84,600

#### 后台重试退让期

**BackgroundRetryMaximumPeriod** 条目定义将备份重试的最大间隔。 例如，如果第一次重试在 10 分钟后，第二次重试将在 20 分钟后，下一次重试将在 30 分钟之后。 这将继续，直到达到 BackgroundRetryMaximumPeriod **条目中的**值。 然后，**BackgroundRetryBackoffPeriod** 值用于重试间隔，直到达到 BackgroundRetryQuitTime **条目中的**值。

子项：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters`  
条目：BackgroundRetryMaximumPeriod  
类型：DWORD  
建议的值（秒）：84,600 秒

#### 后台重试退出时间

当程序对域控制器运行定期搜索并且找不到域控制器时，此条目中设置的值将确定重试何时可能。  
子项：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters`  
条目：BackgroundRetryQuitTime  
类型：DWORD  
建议的值（秒）：600

#### 最大密码期限

指定系统更改本地计算机的计算机帐户密码的频率。 仅当系统配置为按设置间隔自动更改计算机密码时，才使用此条目。 也就是说，仅当 DisablePasswordChange **条目的值**为 **0** 时，才使用此条目。 有关详细信息，请参阅 [“域成员：禁用计算机帐户密码更改](/zh-cn/windows/security/threat-protection/security-policy-settings/domain-member-disable-machine-account-password-changes)”。

子项：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters`  
条目：MaximumPasswordAge  
类型：DWORD  
默认值（十进制，天数）：7（在 Windows NT 中），30 （Windows 2000/XP/2003） 建议的范围：42 到 70

### DFS 注册表设置

DFS **DfsDcNameDelay** 条目的域控制器查询频率可以降低分布式文件系统（DFS）的域控制器查询的频率。 在客户端计算机上修改此项。

子项：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters`  
条目：DfsDcNameDelay  
类型：DWORD  
默认值（分钟）：15

DfsDcNameDelay  ****的有效范围为** 15** 到 **360** 分钟。 新设置无需重启即可生效。

#### DFS 的 PDC 查询频率

说明：具有基于域的 DFS 根的每个 DFS 服务器都会轮询 PDC 以获取根对象上的更改。 可以通过在 DFS 根服务器或服务器上设置 **SyncIntervalInSeconds** 注册表项来控制轮询之间的间隔。 通过设置此项，可以控制 DFS 何时返回基于缓存数据的引用。 如果增加此值，则 DFS 会缓存命名空间和引用，持续时间较长。

子项：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\DFS`  
条目：SyncIntervalInSeconds  
类型：DWORD  
默认值（秒）：3,600 （1 小时）

另请查看以下有关 DFS 卷设置的技术文章：

- [更改客户端缓存引用的时间量](/zh-cn/windows-server/storage/dfs-namespaces/change-the-amount-of-time-that-clients-cache-referrals)

### 知识一致性检查器 （KCC） 复制拓扑更新

知识一致性检查器（KCC）复制拓扑更新可能会导致 WAN 流量创建或验证复制链接。 对于按按流量计费的链接分隔的域控制器，减少 KCC 运行的频率是有意义的。

**说明**：Repl 拓扑更新周期（秒）值定义间隔之间的秒数。

子项：`HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\NTDS\Parameters`  
条目：重新pl 拓扑更新周期（秒）  
类型：DWORD  
默认值（秒）：900 （15 分钟）

### 组策略设置

以下策略设置控制基于 Net Logon 的流量和基于 DFS 的流量的频率。 若要找到这些设置，请单击“开始”，单击**“运行**”**，键入 *gpedit.msc*，然后单击“**确定**”。** 或者，在基于域的组策略对象中编辑它们。

#### 计算机配置/管理模板/系统/Net 登录

- **Scavenge 间隔**
- **非后台调用方的积极定期 DC 缓存刷新**
- **后台调用方的积极定期 DC 缓存刷新**
- **后台调用方的最终 DC 发现重试设置**
- **后台调用方的最大 DC 发现重试间隔设置**
- **后台调用方的初始 DC 发现重试设置**
- **负 DC 发现缓存设置**
- **登录失败时联系 PDC**
- **登录时的预期拨号延迟**

#### 计算机配置/管理模板/网络

设置 DFS 客户端发现 DC 的频率

默认情况下，DFS 客户端每隔 15 分钟尝试发现域控制器。 如果启用 **“设置 DFS 客户端发现 DC** 设置的频率”，则可以更改间隔。 以分钟为单位指定此值。 如果禁用此设置或未配置此设置，则默认值为 15 分钟。 相应的注册表子项如下所示： `HKEY_LOCAL_MACHINE\Software\Policies\Microsoft\System\DFSClient\DfsDcNameDelay`

## 第 2 部分：默认值

### 数据包类型的默认值

下表显示了数据包类型及其默认发送间隔。

| 数据包类型 | 协议 | 运输 | 时间间隔 | 备注 |
| --- | --- | --- | --- | --- |
| NetLogon | 服务器消息块 (SMB) | TCP/IP | 300 秒 |  |
| 浏览 | SMB | TCP/IP | 720 秒 |  |
| KeepAlive | 网络基本输入/输出系统（NetBIOS） | TCP/IP | 3,600 秒 （60 分钟） |  |
| 通过 TCP/IP 回显 NetBIOS （NetBT） | NetBIOS | TCP/IP | 120 秒 | 如果会话处于空闲状态，则文件服务器按指定的间隔发送 SMB 回显帧。 |
| Windows 资源管理器 | SMB | TCP/IP | 32 秒 | 此值控制文件服务器只要客户端打开未完成的长期请求，文件服务器就会向客户端发送 SMB 回显帧的频率。 |
| KeepAlive | NetBIOS | TCP/IP | 300 秒（5 分钟） | 此项对应于  `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlServices\NetBT\parameters\SessionKeepAlive` |
| KeepAlive | TCP | TCP/IP | 1 秒 | 此项对应于  `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\TCPIP\Parameters\KeepAliveTime` |

注意

- 此表中的“浏览”数据包类型指示 PDC（域主浏览器）和主浏览器之间的网络流量。
- Windows LAN 管理器重定向程序每隔 30 秒或 32 秒回显一个 SMB 回显帧，该帧与具有未完成的关联长期请求的每个文件服务器回显一次。 例如，文件服务器可能在 **Microsoft Internet Explorer 中有 NotifyChange** 请求。 若要避免这些数据包，可以设置 **NoRemoteChangeNotify** 密钥。

有关详细信息，请参阅以下知识库文章： [3212430](https://support.microsoft.com/help/3212430) Windows Server 中的 DFSR 复制合作伙伴上不会立即显示文件夹的安全设置更改

- 如果客户端和服务器之间没有针对 KeepAlive 间隔（120 秒）的数据传输，服务器将发送第一个保持连接探测。 在两分钟处于非活动状态（空闲树连接）后，文件服务器发送一条 1 字节会话消息。 TCP 有效负载为“02”。TCP 序列号从上次接收的确认 （ACK） 减 1 开始，并在当前确认中结束。
- 如果使用命名管道对服务器建立连接，则服务器大约每 300 秒向客户端发送一条“NetBT： SS - 会话保持活动”消息。

  “NetBT SessionKeepAlive”条目位于以下注册表子项中： `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\NetBT\Parameters`
- 常见的 Internet 文件系统 （CIFS） TCP 会话保持活动消息包括具有0x85值的字节，后跟 NetBT 标头中具有 0（零）值的三个字节。 如果未为客户端可配置的间隔发送消息，则可能会发送保持活动消息。

### 服务的默认值

| 组件 | 默认间隔设置 | 备注 |
| --- | --- | --- |
| Net Logon 域控制器发现 | 3,600 秒 （60 分钟） |  |
| 域控制器的 DFS 查询 | 900 秒 （15 分钟） |  |
| GPO 刷新间隔 | 90 分钟 | 请参阅组策略说明： [组策略搜索](https://gpsearch.azurewebsites.net/#341) |
| 时间服务 （W32time） | 17 分钟 | 此值位于以下注册表子项中：   `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\W32time\Config\MaxPollInterval` `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\W32time\Config\MinPollInterval`   另请参阅 Windows 时间服务的组策略设置：[全局配置设置](https://gpsearch.azurewebsites.net/#2612)[配置 Windows NTP 客户端](https://gpsearch.azurewebsites.net/#2613) |

## 参考

有关更多信息，请参阅以下知识库文章：

- 314053 Windows XP 的 TCP/IP 和 NBT 配置参数
- [3212430](https://support.microsoft.com/help/3212430) Windows Server 中的 DFSR 复制合作伙伴上不会立即显示文件夹的安全设置更改

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/settings-for-minimizing-periodic-wan-traffic)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
