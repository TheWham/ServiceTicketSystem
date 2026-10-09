# 如果建立 VPN 连接，Windows 连接管理器断开 WLAN 连接

本文提供了 Windows 连接管理器在建立 VPN 连接时断开连接 WLAN 的问题的解决方法。

*适用于：*Windows 8 专业版  
*原始 KB 编号：* 2919900

## 症状

请参考以下方案：

- 启动 Windows 8 客户端。 它自动连接到 WLAN。
- 在 Windows 8 客户端上建立虚拟专用网络（VPN）连接。
- 成功建立 VPN 隧道大约 20 秒后，WLAN 连接断开。

## 原因

出现此问题的原因是 VPN 适配器注册为以太网适配器。

若要检查此项，请打开注册表编辑器，然后浏览到以下项：

`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}\xxxx`

`"*IfType"=dword:00000006 ==> IF_TYPE_ETHERNET_CSMACD`

注意

xxxx 对应于下面的数字，你可以找到 VPN 适配器的名称。 如果 IfType 的值等于 6，则适配器被视为以太网适配器。

从 Windows 8 开始，WCMSVC（Windows 连接管理器）会断开 WLAN 连接，因为以太网适配器被视为更可靠，并且与 WLAN 连接相比提供更好的性能。 在决策过程中将考虑以下各项：

- 适配器类型，以太网，无线，虚拟
- 适配器是否保留默认网关和默认路由？
- 网络适配器是否已成功连接到 Internet 的网络连接状态指示器（NCSI）探测？
- 客户端的域是否可以在适配器上访问？

## 解决方法

使用组策略或本地将 Windows 连接管理器 GPO 配置为“已禁用”。

1. 打开本地组策略编辑器，然后转到计算机配置\管理模板\网络\Windows 连接管理器
2. 将同时连接到 Internet 或 Windows 域**的连接数更改为“已禁用”的设置**

## 详细信息

或者，可以将 VPN 接口的 IfType 更改为与以太网不同的值。

注意

更改此设置可能会对 VPN 适配器的功能产生一些副作用。 请联系 VPN 客户端的制造商获取详细信息。

可在此处找到不同适配器类型的值：  
[https://msdn.microsoft.com/library/aa814491(VS.85).aspx](https://msdn.microsoft.com/library/aa814491%28vs.85%29.aspx)  
[https://msdn.microsoft.com/library/windows/hardware/ff565767(v=vs.85).aspx](https://msdn.microsoft.com/library/windows/hardware/ff565767%28v=vs.85%29.aspx)

适用于 VPN 适配器的合适值为：

`IF_TYPE_PROP_VIRTUAL 53 (0x35) Proprietary virtual/internal`

`IF_TYPE_TUNNEL 131 (0x83) Encapsulation interface`

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/windows-connection-manager-disconnects-wlan)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
