# 排查 DNS 动态更新问题

本指南解决了与域名系统（DNS）动态更新相关的常见问题，并提供相关的故障排除步骤。 动态更新对于维护准确的 DNS 记录至关重要，尤其是在 IP 地址频繁更改的环境中，例如动态主机配置协议（DHCP）。 本指南介绍 DNS 客户端、DHCP 服务器和 DNS 服务器的常见方案、建议和故障排除提示。

## 一般原因

下面是动态更新失败的一般原因：

- DNS 客户端不会发送动态更新。
- DHCP 应更新记录，但该功能未按预期工作。
- 由于权限问题，DNS 服务器不会更新记录。

在进行故障排除之前，我们建议你实现以下最佳做法。

## Microsoft标准建议

### 客户端 DNS 注册

在许多环境中，DHCP 代表客户端更新 DNS 记录。 鉴于这些天基础结构的混合性质以及使用虚拟专用网络（VPN）连接到办公室的员工，通常有多个与一个终结点关联的 IP。 如果客户端注册其记录，则可以避免这种情况。 因此，建议不要使用 DHCP 选项 81，而是让客户端注册其记录。

有关 DHCP 选项 81 的工作原理的详细信息，请参阅以下两篇文章：

- [2.2.7 DHCPv4 选项代码 81 （0x51） - 客户端 FQDN 选项](/zh-cn/openspecs/windows_protocols/ms-dhcpe/e4c46e9d-5013-4ab0-9434-ccd11f1347f5)
- [如果 DHCP 服务器使用“始终动态更新 DNS 记录”](../../windows-server/networking/dns-registration-behavior-when-dhcp-server-manages-dynamic-dns-updates) ，则出现意外的 DNS 记录注册行为（本文提到 Windows DNS 客户端行为）。

### 将动态更新配置为“仅限安全”

域区域中的动态更新应仅**配置为**“安全”。

如果执行动态注册的客户端计算机已加入域（应由域管理员或解决方案架构师验证），请将域区域配置为允许使用 **Secure** 进行动态更新，以确保动态注册上的一致行为。

### 为动态记录启用时间戳

默认情况下，动态记录不包含时间戳。 配置区域属性时，可以在区域属性对话框的“老化**”部分下**启用 **Scavenge Stale Records** 选项。 启用此选项后，新注册的记录将包含时间戳。

如果计划对过时记录进行复仇，则需要时间戳。 如果没有时间戳，DNS 记录无法与当前时间进行比较，也不会被视为过时，即使它已动态注册也是如此。

注意

如果最近启用了给定选项，则更改之前注册的记录不会携带时间戳或清理。

### AD 集成区域中 DNS 的 Scavenge 设置

**区域老化**属性中的 Scavenge** Stale Records** 选项可确保 Active Directory （AD） 对象携带时间戳。 但是，过期记录的实际清理发生在 DNS 服务器级别，影响启用此设置的所有区域。 有关清理的详细说明，请参阅 [DNS 清理设置](../../windows-server/networking/dns-scavenging-setup)。

清理周期是 DNS 进程的低优先级线程，因此它可能并不总是一致地运行。 若要最大程度地提高其运行机会，请在 AD 集成区域环境中在域控制器 （DC） DNS 服务器上配置清理，这些服务器没有关键角色，例如灵活单主操作（FSMO）角色，尤其是避免主域控制器 （PDC） 模拟器。 理想情况下，应在 DC 上设置清理，而无需任何 FSMO 角色。 如果此配置不可行，请避免在 PDC 模拟器上对其进行配置。

### 维护标准 DNS 区域权限

标准 DNS 区域权限应保持不变。

在 AD 集成的区域设置中，权限遵循类似于新技术文件系统（NTFS）或文件系统的标准层次结构。 这意味着，如果帐户有权创建、删除或修改区域及其子对象，则可以执行这些操作。 默认情况下，只有企业管理员（林范围）和域管理员（域范围）才拥有这些权限。

启用“仅**安全动态更新”后**，如果帐户是该记录的所有者，则经过身份验证的帐户（例如加入域的计算机）可以更新、删除或修改 DNS 记录。 这可确保只有记录的原始创建者可以修改或删除记录，这是仅安全动态更新的预期行为。

但是，当 DHCP 服务器使用完全限定的域名（FQDN）DHCP 选项（选项 81）代表客户端更新 DNS 记录时，可能会出现挑战。 在这种情况下，可能会发生不一致，因为 DHCP 服务器更新的 DNS 记录不能由原始客户端修改，反之亦然。

如前所述，我们建议客户端计算机更新自己的 DNS 记录，而不是依赖于 DHCP 服务器。 这是因为有几个原因，Microsoft还实施了设计更改来强制实施此行为。 此更改可防止 DHCP 服务器同时更新客户端的 A 和 PTR 记录。 若要替代此行为，如果 DHCP 服务器使用“始终动态更新 DNS 记录”[，请参阅](../../windows-server/networking/dns-registration-behavior-when-dhcp-server-manages-dynamic-dns-updates)意外的 DNS 记录注册行为。

理想情况下，客户端应更新自己的 DNS 记录。 但是，如果记录以前由 DHCP 服务器更新，则实际客户端将无法对其进行修改。 为了解决此问题，一些企业强制 DHCP 服务器继续更新客户端的记录，这强烈建议不要这样做。

建议的方法是允许 DHCP 服务器或清理过程删除记录。 删除后，客户端可以更新它们。

### 将 DHCP 服务器与 ADDS 分开

DHCP 服务器应托管在单独的服务器上，而不是托管在运行 Active Directory 域服务 （ADDS） 的 DC 上。

在安全更新设置中，DHCP 服务器使用其计算机的域帐户注册 DNS 记录。 DHCP 服务器在 DC 上运行时，它使用 DC 的帐户注册记录。 这意味着，如果启用了 FQDN 选项且 DHCP 服务器未配置专用服务帐户，则 DHCP 服务器可以覆盖静态记录。 这可能会导致意外清理静态记录等问题。

为防止此类问题，应使用服务帐户配置 DHCP 服务器，并在单独的服务器上运行。 有关详细信息，请参阅 [如何在 Windows](../../windows-server/networking/configure-dns-dynamic-updates-windows-server-2003) 中配置 DNS 动态更新。

## 排查常规和已知问题

### 客户端问题

- 找不到授权开始（SOA）。
- 客户端不会发送动态更新。 有关详细信息，请参阅 [如何在 Windows](../../windows-server/networking/enable-disable-dns-dynamic-registration) 中启用或禁用 DNS 更新。
- 客户端无法从 DC 获取身份验证票证事务签名（TSIG）。

### DHCP 服务器问题

- DHCP 服务器不会代表客户端发送动态更新。
- DHCP DNS 更新队列长度。 有关详细信息，请参阅 [DNS 注册的 DHCP 动态更新延迟或未处理](../../windows-server/networking/dhcp-dynamic-updates-of-dns-registrations-delayed)。
- DHCP 尝试更新客户端记录时发生冲突，因为它已在客户端的计算机帐户中注册。 有关详细信息，请参阅 [DHCP 服务器是否使用“始终动态更新 DNS 记录”](../../windows-server/networking/dns-registration-behavior-when-dhcp-server-manages-dynamic-dns-updates)时出现意外的 DNS 记录注册行为。

### DNS 服务器问题

- DNS 区域的权限问题。
- DNS 区域级别的经过身份验证的帐户设置中的更改。
- DHCP 为动态更新配置服务帐户。

## 排查 DNS 动态更新问题

注意

此多部分讨论从 Windows 客户端到服务器的各个方面，这些问题在发生此类问题时应进行检查。

需要首先进行基本检查，例如确定问题是影响多个客户端、同一子网上的客户端还是特定客户端。 这有助于缩小问题是否在于客户端、服务器或网络。 有关如何触发 DNS 动态更新的说明，包括示例，请参阅 [如何在 Windows](../../windows-server/networking/configure-dns-dynamic-updates-windows-server-2003#how-windows-based-computers-update-their-dns-names) 中配置 DNS 动态更新。

了解 DNS 动态更新后，可以使用以下清单来确保客户端的动态更新设置已到位。

### DNS 客户端清单

检查是否 **在 DNS** 中注册此连接的地址：

```
#Get the list of interfaces that are up and connected.
$Adapters = Get-NetAdapter | Where-Object Status -eq Up

#If there's only one interface, the following command will work.
Get-DnsClient -InterfaceIndex $Adapters.ifIndex

#If more than one interface is active and up, you can use "Get-DNSClient" to see the registration status of all interfaces.
```

在输出中， **RegisterThisConnectionsAddress** 应为 **True**。 如果值为 False，请将值更改为 **True****：**

```
#Get the list of interfaces that are up and connected.
$Adapters = Get-NetAdapter | Where-Object Status -eq Up

#If there's only one interface, the following command will work.
Set-DnsClient -RegisterThisConnectionsAddress $True -InterfaceIndex $Adapters.ifIndex
```

通过获取 `Get-DnsClient` 输出来验证值，并确保 **RegisterThisConnectionsAddress** 设置为 **True**。

有一个组策略可以修改此行为。 默认情况下，网络接口设置为注册其连接。 但是，企业可以使用 **动态更新** 组策略设置来控制客户端发送 DNS 动态更新的方式。 组策略位于：

**计算机配置**>**管理模板****>网络****>DNS 客户端**>**动态更新**

### DNS 服务器端清单

#### 确保区域可写

动态注册客户端的域必须是可写复制区域。 这意味着区域应包含托管它的 DNS 服务器的 SOA 记录，并且客户端必须能够通过网络访问此服务器。

通常有两种类型的设置：

1. 指向仅缓存 DNS 服务器的客户端：此 DNS 服务器不托管任何域区域，但使用条件转发器或转发器指向包含区域（可写或可读）的实际 DNS 服务器。
2. 简单设置：客户端直接指向托管域区域的 DNS 服务器。

通常选择选项 1 进行负载均衡，并使用多个客户端选择更大的环境。 其思路是将名称解析负载从可用的 DC 转移到额外的服务器。 但是，在此设置中，客户端必须与托管域区域的 SOA 记录的服务器建立 DNS 协议的连接。 否则，动态更新将失败。

#### 允许动态更新

Microsoft DNS 服务器上托管的 AD 集成 DNS 区域有三个选项用于动态更新：

- **无**
- **不安全和安全**
- **仅限安全**

注意

最后一个选项仅适用于 AD 集成的 DNS 区域。

若要允许动态更新，应将**区域配置为“不安全且安全”或**“仅限**安全的**更新类型”。 **建议仅** 对 AD 集成区域使用安全。

#### 检查 DNS 审核

DNS 服务器日志记录在 DNS 日志记录和诊断[中](/zh-cn/previous-versions/windows/it-pro/windows-server-2012-R2-and-2012/dn800669(v=ws.11))进行了讨论。 具体而言，它旨在验证所关注的记录是否已注册，并可以使用 DNS [审核事件](/zh-cn/previous-versions/windows/it-pro/windows-server-2012-R2-and-2012/dn800669(v=ws.11)#audit-events)（事件 ID 519）进行跟踪。 可以使用给定 ID 筛选默认启用的 DNS 审核事件，并验证记录是否已成功注册。

注意

审核事件日志是给定 DNS 服务器的本地日志，这意味着给定 ID 仅在注册记录的 DNS 服务器上可见。

### 方案：DHCP 服务器无法代表客户端完成动态更新，或者注册延迟

DHCP 服务器配置为更新 DHCP 客户端的记录。 配置在 [Windows 中如何配置 DNS 动态更新中](../../windows-server/networking/configure-dns-dynamic-updates-windows-server-2003#how-dhcpdns-update-interaction-works)指定。 Windows 客户端还配置为遵循 DHCP 选项 81。 当 DHCP 服务器管理动态 DNS 更新[时，它们被配置为意外的 DNS 记录注册行为中所述](../../windows-server/networking/dns-registration-behavior-when-dhcp-server-manages-dynamic-dns-updates)。

注意

建议客户端注册其记录，而不是 DHCP 或任何其他设备。

所有配置都已到位，DNS 记录可能会进行大量延迟注册，或者根本无法注册。 可以通过检查位于 C：\Windows\System32\DHCP *的每日审核文件中*的 DHCP 服务器审核日志来验证这一点。

重要

DNS 注册的 DHCP 动态更新会 [延迟或未处理](../../windows-server/networking/dhcp-dynamic-updates-of-dns-registrations-delayed)类似的问题。

#### 原因

出现此问题的原因有多种，但常见的原因是 DHCP 服务器的 DNS 动态更新队列已满，这意味着它无法处理新请求。 此问题通常发生两个主要原因：

1. DNS 服务器（在 DHCP 作用域中配置）不会返回 SOA 响应，因为 SOA 查询用于 DNS 服务器上未配置的反向查找区域。
2. SOA 服务器上不允许有 SOA 响应或动态更新。 有关详细信息，请参阅 [DNS 注册的 DHCP 动态更新延迟或未处理](../../windows-server/networking/dhcp-dynamic-updates-of-dns-registrations-delayed)。

#### 解决方法：在 DNS 服务器上创建反向查找区域

##### 方法 1

检查并咨询网络团队和 DHCP 配置，以获取网络中所有作用域/子网的列表。 为每个此类子网创建反向查找。 此方法适用于 IPv4 和 IPv6 反向查找区域。

##### 方法 2

为了避免任何遗漏，请创建具有专用 IP 根范围的区域。 例如：

- 168.192.in-addr.arpa
- 16.172.in-addr.arpa
- 10.in-addr.arpa

这包括环境中 IPv4 地址的所有子网范围。 如果已创建一些反向查找区域，它们将自动成为这些区域中的委派。

#### 说明

配置 DHCP 选项 81 时，DHCP 服务器会检查客户端返回的 FQDN，并从作用域中配置的 DNS 服务器请求其 SOA。 如果未返回 SOA，请求将排队等待重试。 当缺少反向查找区域时，队列往往会填满，因为会请求每个租约，但没有区域注册 PTR 记录。 同样，对于前向查找，如果在 SOA 服务器上禁用动态更新或无法访问 SOA 服务器，队列也会填满。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/troubleshooting-dns-dynamic-update-issues)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
