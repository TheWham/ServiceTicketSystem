# 使用 IP-HTTPS 时，DirectAccess 客户端可能无法连接到 DirectAccess 服务器并出现错误0x800b0109

本文提供了一个解决方案，说明 DirectAccess 客户端无法使用 IP-HTTPS 连接到服务器的问题。

*原始 KB 数：* 2980667

## 现象

DirectAccess 客户端可能无法使用 IP-HTTPS 连接到 DirectAccess 服务器。 运行 `netsh interface http show interface` 命令时，输出如下所示：

> URL：错误： `https://da.contoso.com:443/IPHTTPS` 0x800b0109  
> 接口状态：无法连接到 IPHTTPS 服务器。 正在等待重新连接
>
> 错误0x800b0109转换为：  
> “CERT\_E\_UNTRUSTEDROOT”  
> #已处理证书链，但在根目录中终止  
> 信任提供程序不信任的 # 证书。

默认情况下，受信任的根证书颁发机构证书存储区配置了一组由 Windows 客户端信任的公共证书颁发机构。 某些组织可能想要管理证书信任，并阻止域中的用户配置自己的受信任的根证书集。 此外，某些组织可能希望从自己的证书颁发机构服务器为 IP-HTTPS 服务器颁发证书。 他们需要分发该特定的受信任根证书才能启用信任关系。 为 DirectAccess 配置证书时，客户端必须信任根证书颁发机构，并且该证书应具有受信任的根证书颁发机构存储中的根 CA 证书。

有关证书的详细信息，请参阅 [证书吊销的工作原理](/zh-cn/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/ee619754(v=ws.10))。

## 原因

IP-HTTPS 证书的颁发证书颁发机构在客户端受信任和中间存储中不存在。 请确保将根证书添加到根存储，并将中间证书添加到中间存储。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 获取颁发 IP-HTTPS 证书的证书颁发机构的证书。
2. 将此证书导入 DirectAccess 客户端的计算机存储中。
3. 若要将此更改应用于所有客户端， [请使用组策略部署导入的证书](/zh-cn/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/cc772491(v=ws.11))。

## DirectAccess 连接方法

DirectAccess 客户端使用多种方法连接到 DirectAccess 服务器，这样就可以访问内部资源。 客户端可以选择使用 Teredo、6to4 或 IP-HTTPS 连接到 DirectAccess。 这也取决于 DirectAccess 服务器的配置方式。

当 DirectAccess 客户端具有公共 IPv4 地址时，它将尝试使用 6to4 接口进行连接。 但是，某些 ISP 提供公共 IP 地址的错觉。 他们向最终用户提供的内容是伪公共 IP 地址。 这意味着 DirectAccess 客户端（数据卡或 SIM 连接）收到的 IP 地址可能是来自公共地址空间的 IP，但实际上位于一个或多个 NAT 后面。

当客户端位于 NAT 设备后面时，它将尝试使用 Teredo。 许多企业（如酒店、机场和咖啡店）不允许 Teredo 流量穿过防火墙。 在这种情况下，客户端将故障转移到 IP-HTTPS。 IP-HTTPS 是基于 SSL （TLS） TCP 443 的连接生成的。 SSL 出站流量很可能在所有网络上都允许。

考虑到这一点，IP-HTTPS 已生成，以提供可靠且始终可访问的备份连接。 当其他方法（如 Teredo 或 6to4）失败时，DirectAccess 客户端将使用此客户端。

有关转换技术的详细信息，请参阅 [IPv6 转换技术](/zh-cn/previous-versions//bb726951(v=technet.10))。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/directaccess-clients-connection-error-0x800b0109)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
