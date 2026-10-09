# 清除“在 DNS 中注册此连接的地址”选项不会使用静态 IP 地址删除 Windows 客户端的 DNS 记录

## 症状

清除客户端计算机上的 **DNS 复选框中的“注册此连接的地址** ”后，客户端不会从服务器中删除其域名系统（DNS）记录。 有关设置的详细信息，请参阅以下屏幕截图：

![“高级 TCP/IP 设置”窗口的屏幕截图，其中未选中“在 DNS 中注册此连接的地址”。](media/clear-register-addresses-not-remove-dns-records/register-connection-address-dns.png)

## 决议

若要解决此问题，请根据客户端计算机的配置执行以下步骤。

### 对于配置为使用静态 IP 地址的客户端计算机

如果客户端计算机使用静态 IP 地址，请按照客户端计算机上的以下步骤从 DNS 服务器中删除记录：

1. 清除 **DNS 复选框中的“注册此连接地址** ”。
2. 触发 DNS 记录的注册。 为此，请使用按首选项顺序列出的以下步骤之一：

   - 重启 DNS 客户端服务。
   - 重启基于 Windows 的计算机。
   - 以管理员身份打开命令提示符窗口，然后运行 `ipconfig /registerdns` 该命令。

注释

如果使用动态主机配置协议（DHCP）地址配置了多宿主客户端或服务器上的一个或多个适配器，请参阅“对于配置为使用动态 IP 地址的客户端计算机”部分中的最后一条说明。

### 对于配置为使用动态 IP 地址的客户端计算机

如果将客户端计算机配置为使用 DHCP 获取 IP 地址，则客户端或 DHCP 服务器将在清除 **DNS 复选框中的“注册此连接的地址** ”后尝试删除动态注册的记录。

注释

清除 TCP/IPv4 或 TCP/IPv6 **的“高级 TCP/IP 设置**”属性窗口的“DNS”选项卡上的**“在 DNS 中注册此连接的地址**”复选框后，将从该计算机的本地注册表中删除以下节点：

`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\DNSRegisteredAdapters\{<36 character GUID corresponding to the network adapter that TCPIP was bound to>}`

这适用于使用静态 IP 地址的客户端以及使用动态 IP 地址的客户端。

注释

如果适配器配置为在计算机上使用动态 IP 寻址（DHCP），请不要运行 `ipconfig /registerdns` 该命令。 动态 IP 寻址使用 DHCP 服务器来注册“PTR”记录，并根据需要代表 DHCP 客户端托管“A”和“AAAA”记录。 DHCP 服务器配置确定如何添加“A”和“AAAA”注册。 运行 `ipconfig /registerdns` 此命令后，将使用本地计算机的安全描述符注册 DNS 记录。 这可以防止 DHCP 服务器更新这些记录，直到手动删除记录。 重述，如果 DHCP 服务器没有更新 DNS 记录的权限，则 DHCP 注册将无提示失败。

对于 DHCP 客户端，建议执行以下步骤：

1. 重启“DNS 客户端”服务。 为此，请运行以下命令：

   ```
   net stop DNSCACHE
   net start DNSCACHE
   ```
2. 运行以下命令来更新 DHCP 客户端的 DNS 注册：

   ```
   ipconfig /release
   ipconfig /renew
   ```

有关详细信息，请参见:

- [DNS 进程和交互](/zh-cn/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/dd197552(v=ws.10))。
- [有关 IPv4 和 IPv6 高级 DNS 选项卡的常规信息](/zh-cn/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/cc754143(v=ws.11))。

## 详细信息

若要确定网络适配器是使用静态 IP 地址还是动态 IP 地址，请执行以下步骤：

1. 打开命令提示符窗口。
2. 运行 `ipconfig /all` 命令。
3. 在返回的结果中，如果网络适配器下的 **DHCP 已启用** 字段显示为 **“是**”，则网络适配器正在使用动态 IP 地址。 如果显示为 **“否**”，则网络适配器正在使用静态 IP 地址。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/clear-register-addresses-not-remove-dns-records)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
