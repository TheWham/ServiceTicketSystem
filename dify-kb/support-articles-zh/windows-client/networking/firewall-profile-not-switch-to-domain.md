# 使用第三方 VPN 客户端时，Windows 防火墙配置文件不会始终切换到域

本文解决了使用第三方 VPN 客户端连接到域网络时 Windows 防火墙配置文件不会从公共或专用切换到域的问题。

*适用于：* Windows 10 – 所有版本  
*原始 KB 数：* 4550028

## 现象

使用第三方虚拟专用网络（VPN）客户端连接到域网络。 在此方案中，Windows 防火墙并不总是按预期从公共或专用配置文件切换到域配置文件。

## 原因

某些第三方 VPN 客户端中的时间延迟有时会导致此问题。 当客户端将必要的路由添加到域网络时，会发生延迟。

## 解决方法

若要解决此问题，建议联系 VPN 提供程序以获取解决方案，以减少添加域路由导致的时间滞后时间。

对于 VPN 提供程序，一旦 VPN 适配器到达 Windows，就可以使用回调 API 添加路由。 例如：

- **NotifyUnicastIpAddressChange**：向调用方发出对任何 IP 地址的任何更改（包括 DAD 状态更改）的警报。
- **NotifyIpInterfaceChange**：注册一个回调，以通知所有 IP 接口的更改。

在用户模式下，有 IpHelper API。 例如：

- **NotifyAddrChanget**：通知用户地址更改。

## 解决方法

重要

请认真遵循本部分所述的步骤。 如果注册表修改不正确，可能会发生严重问题。 在修改注册表之前，请[备份注册表](https://support.microsoft.com/help/322756)，以便在出现问题时可以还原。

若要解决此问题，请在重试域检测时禁用负缓存，以帮助网络位置感知 （NLA） 服务。 为此，请使用以下方法。

- 首先，通过将 NegativeCachePeriod **注册表项添加到**以下子项来禁用域发现负缓存：

  `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\NetLogon\Parameters`

  名称： **NegativeCachePeriod**  
  类型： **REG\_DWORD**  
  值数据：0**（默认值：****45** 秒;设置为 **0** 以禁用缓存）
- 如果问题无法解决，请通过将 MaxNegativeCacheTtl **注册表项添加到**以下子项来进一步禁用 DNS 负缓存：

  `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Dnscache\Parameters`

  名称： **MaxNegativeCacheTtl**  
  类型： **REG\_DWORD**  
  值数据：0**（默认值：5** 秒;设置为 **0** 以禁用缓存）

## 详细信息

出现问题时，事件流如下所示：

- 用户连接到 VPN。
- 在 VPN 隧道设置期间，将创建 VPN 接口并分配 IP 地址，并将必要的路由添加到接口。 以下条件适用：
  - 在以下情况之一中，TCP/IP 会立即添加主机路由和链接子网路由：

    - 该地址的类型为特定类型，例如 DHCP、IPv6 链接本地和 IPv6 临时地址。
    - 为该地址启用了乐观重复地址检测（DAD）。

    否则，TCP/IP 会在 DAD 成功完成后添加这些路由。
  - VPN 客户端负责 VPN 网络所需的路由，例如使 VPN 接口可路由到 VPN DNS 服务器。
- 第一个路由更改触发网络连接状态指示器（NCSI）检测。 网络位置感知（NLA）服务尝试向域控制器进行身份验证，以将正确的配置文件分配给防火墙。
- 身份验证首先让 NLA 服务调用 **DsGetDcName** 函数来检索 DC 名称。 它由名称的 DNS 名称解析完成，例如 as\_ldap.\_tcp。CNNDC.\_sites.dc.\_msdcs。<domainname>。
- 如果在将所需的 VPN 路由添加到 VPN 接口之前发生此名称解析，则此 DNS 名称解析将失败。 它返回“DsGetDcName 函数失败并ERROR\_NO\_SUCH\_DOMAIN。然后，缓存此结果。
- DNS 名称解析失败也可能创建负 DNS 缓存。 当 NLA 服务重试域检测时，负缓存会导致其他失败。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/firewall-profile-not-switch-to-domain)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
