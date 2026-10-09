# 尝试通过基于 Windows Server 的远程访问服务器建立 VPN 连接时，会收到“错误 721”错误消息

本文提供了错误 721 的解决方案，该错误在尝试通过基于 Windows Server 的远程访问服务器建立 VPN 连接时发生。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 888201

## 现象

如果尝试使用点到点隧道协议（PPTP）客户端建立与企业网络的虚拟专用网络（VPN）连接，则与基于 Windows Server 的远程访问服务器的Microsoft连接可能无法成功。 可能会收到以下错误消息：

> 错误 721：远程计算机未响应。

注意

721 错误说明可能有所不同。

## 原因

如果网络防火墙不允许通用路由封装（GRE）协议流量，则可能会出现此问题。 GRE 是 IP 协议 47。 PPTP 将 GRE 用于隧道数据。

## 解决方法

若要解决此问题，请将网络防火墙配置为允许 GRE 协议 47。 此外，请确保网络防火墙允许端口 1723 上的 TCP 流量。 必须满足这两种条件才能使用 PPTP 建立 VPN 连接。

## 详细信息

有关在 Windows Server 2003 中安装和配置 VPN 服务器的详细信息，请单击以下文章编号以查看Microsoft知识库中的文章：

323441如何在 Windows Server 2003 中安装和配置虚拟专用网络服务器

有关 PPTP 协议的详细信息，请访问以下Microsoft网站： <https://technet.microsoft.com/library/bb877963.aspx>

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/error-when-establishing-vpn-connection)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
