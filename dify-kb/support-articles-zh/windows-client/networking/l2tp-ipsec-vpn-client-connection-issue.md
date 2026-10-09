# 如何排查 Microsoft L2TP/IPSec 虚拟专用网络客户端连接问题

本文介绍如何排查 L2TP/IPSec 虚拟专用网络 (VPN) 连接问题。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 325034

## 总结

必须先建立 Internet 连接，然后才能建立 L2TP/IPSec VPN 连接。 如果在建立 Internet 连接之前尝试建立 VPN 连接，可能会遇到长时间延迟（通常为 60 秒），然后可能会收到一条错误消息，指出调制解调器或其他通信设备没有响应或出现问题。

排查 L2TP/IPSec 连接问题时，了解 L2TP/IPSec 连接如何进行非常有用。 启动连接时，初始 L2TP 数据包会发送到服务器，请求建立连接。 此数据包会导致计算机上的 IPSec 层与 VPN 服务器协商，以设置受 IPSec 保护的会话（安全关联）。 IPSec 协商可能需要几秒钟到两分钟左右，具体取决于包括链接速度在内的许多因素。 建立 IPSec 安全关联 (SA) 后，将启动 L2TP 会话。 启动时，将收到提示输入姓名和密码（除非已设置连接以在 Windows Millennium Edition 中自动连接。) 如果 VPN 服务器接受姓名和密码，会话设置将完成。

L2TP/IPSec 连接中的常见配置失败是配置错误或缺少证书，或者配置错误或缺少预共享密钥。 如果 IPSec 层无法与 VPN 服务器建立加密会话，它将在无提示的情况下失败。 因此，L2TP 层看不到对其连接请求的响应。 会有一个较长时间的延迟（通常为 60 秒），然后可能会收到一条错误消息，指出服务器没有响应，或者调制解调器或通信设备没有响应。 如果在收到输入姓名和密码提示之前收到此错误消息，则 IPSec 未建立其会话。 如果发生这种情况，请检查证书或预共享的密钥配置，或将 isakmp 日志发送给网络管理员。

阻止 IPSec 会话成功的第二个常见问题是使用网络地址转换 (NAT)。 许多小型网络使用具有 NAT 功能的路由器在网络上的所有计算机之间共享单个 Internet 地址。 IPSec 的原始版本会删除通过 NAT 的连接，因为它会将 NAT 的地址映射检测为数据包篡改。 家庭网络经常使用 NAT。 除非客户端和 VPN 网关都支持新兴的 IPSec NAT-遍历 (NAT-T) 标准，否则这会阻止使用 L2TP/IPSec。 有关详细信息，请参阅 "NAT 遍历" 部分。

如果在收到输入姓名和密码提示后连接失败，则已建立 IPSec 会话，并且姓名和密码可能存在问题。 其他服务器设置也可能阻止成功建立 L2TP 连接。 在这种情况下，请将 PPP 日志发送给管理员。

## NAT 遍历

借助 Microsoft L2TP/IPSec VPN 客户端中的 IPSec NAT-T 支持，当 VPN 服务器还支持 IPSec NAT-T 时，IPSec 会话可以通过 NAT。 Windows Server 2003 支持 IPSec NAT-T。 Windows 2000 Server 也支持 IPSec NAT-T，并为 Windows XP 和 Windows 2000 提供 L2TP/IPSec NAT-T 更新。

对于第三方 VPN 服务器和网关，请与管理员或 VPN 网关供应商联系，以核实是否支持 IPSec NAT-T。

## 详细信息

配置实用工具还提供启用 IPSec 日志记录的复选框。 如果无法连接，并且网络管理员或支持人员已要求提供连接日志，则可以在此处启用 IPSec 日志记录。 执行此操作时，会在 `C:\Program Files\Microsoft IPSec VPN` 文件夹中创建日志 (Isakmp.log)。 创建连接时，还可在 L2TP 中为 PPP 处理启用日志记录。 为此，请执行以下操作：

1. 右键单击“拨号网络”文件夹，然后单击“属性”。
2. 单击“网络”选项卡，然后单击以选择“记录此连接的日志文件”复选框。

PPP 日志文件为 `C:\Windows\Ppplog.txt`。 它位于 `C:\Program Files\Microsoft IPSec VPN` 文件夹中。

有关详细信息，请参阅 [Microsoft L2TP/IPSec 虚拟专用网络客户端的默认加密设置](https://support.microsoft.com/help/325158)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/l2tp-ipsec-vpn-client-connection-issue)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
