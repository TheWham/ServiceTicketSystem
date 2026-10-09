# 远程过程调用 （RPC） 错误故障排除指南

## 概要

许多程序和服务（例如 Active Directory 复制和Microsoft管理控制台（MMC）都使用远程过程调用（RPC）协议在网络中进行通信。 RPC 通信失败时，可能会看到“RPC 服务器不可用”等错误。下图显示了 RPC 错误的示例。

![显示 RPC 服务器不可用的错误消息的屏幕截图。](media/rpc-errors-troubleshooting/rpc-unavailable.png)

为了帮助你诊断和修复 RPC 连接问题，本文可帮助你了解 RPC 的工作原理以及常见问题的发生方式。 它提供分步指南来帮助解决常见问题。 它还介绍了可用于识别和修复特定于网络拓扑的 RPC 问题的工具。

## RPC 协议基础知识

首先，需要了解几个重要的术语：

- **终结点映射器（EPM）**：在服务器上侦听服务，并使用端口和 UUID 信息将客户端应用引导到服务器应用。 该服务是 RPC 子系统的一部分，用于解析动态终结点以响应客户端请求。 在某些情况下，它会向服务器动态分配终结点。
- **塔**：描述 RPC 协议，使客户端和服务器能够协商连接。
- **楼层**：包含特定数据的塔中的内容层，例如端口、IP 地址和标识符。
- **UUID**：标识 RPC 应用程序的已知 GUID。 在故障排除期间，可以使用 UUID 跟踪单个应用程序类型的 RPC 对话（一次发生在单个计算机上的许多类型中）。
- **Opnum**：标识客户端希望服务器执行的函数。 此值只是十六进制数。 但是，良好的网络分析器会为你转换函数。 如果无法识别该函数，请联系应用程序供应商。
- **端口**：客户端或服务器应用程序的通信终结点。 EPM 为要使用的客户端和服务器分配动态端口（也称为高端口或临时端口）。

  注意

  端口号通常是用于故障排除的最重要信息。
- **存根数据**：在客户端上的函数与服务器上的函数之间交换的数据。 此数据是有效负载，是通信的重要组成部分。

### 连接的工作原理

下图显示了连接到服务器以运行远程操作的客户端。 客户端最初在服务器上联系 TCP 端口 135，然后与 EPM 协商动态端口号。 EPM 分配端口后，客户端会断开连接，然后使用动态端口连接到服务器。

![显示客户端如何与远程服务器建立 RPC 连接的关系图。](media/rpc-errors-troubleshooting/rpc-flow.png)

重要

如果防火墙将客户端和服务器分开，防火墙必须允许在端口 135 和 EPM 分配的动态端口上进行通信。 管理此方案的一种方法是指定要使用的 EPM 的端口或端口范围。 有关详细信息，请参阅 [示例：配置 RPC 如何分配动态端口](#example-configure-how-rpc-allocates-dynamic-ports)。

某些防火墙还允许 UUID 筛选。 在此方案中，如果 RPC 请求使用端口 135 跨越防火墙并联系 EPM，则防火墙会记下分配给请求的 UUID。 当 EPM 响应并发送该 UUID 的动态端口号时，防火墙还会记下端口号。 然后，防火墙允许针对该 UUID 和端口执行 RPC 绑定操作。

### 示例：配置 RPC 如何分配动态端口

默认情况下，EPM 从为 TCP 和 UDP 配置的范围随机分配动态端口（基于使用的操作系统的实现）。 但是，这种方法可能并不可行，尤其是在客户端和服务器必须通过防火墙通信的情况下。 另一种方法是指定要使用的 EPM 的端口号或端口号范围，并在防火墙中打开这些端口。

许多依赖于 RPC 的 Windows 服务器应用程序提供选项（如注册表项）来自定义允许的端口。 Windows 服务对此任务使用 **HKEY\_LOCAL\_MACHINE\SOFTWARE\Microsoft\Rpc\Internet** 子项。

指定端口或端口范围时，请使用超出常用端口范围的端口。 可以在服务概述和 Windows [的网络端口要求中找到](../../windows-server/networking/service-overview-and-network-port-requirements) Windows 中使用的服务器端口和主要Microsoft产品的完整列表。 本文还列出了 RPC 服务器应用程序，并提到哪些 RPC 服务器应用程序可配置为使用 RPC 运行时功能之外的自定义服务器端口。

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 但是，注册表修改不当可能会出现严重问题。 因此，按以下步骤操作时请务必谨慎。 出于防范目的，请在修改之前备份注册表，以便在出现问题时还原注册表。 有关如何备份和还原注册表的详细信息，请参阅：[如何备份和还原 Windows 中的注册表](https://support.microsoft.com/help/322756)。

默认情况下， **Internet** 密钥不存在。 因此，必须创建它。
**对于 Internet** 密钥，可以配置以下条目：

- **端口REG\_MULTI\_SZ**：指定端口或非独占端口范围。 Internet 下显示的其他条目指示这些条目是要使用的端口，还是要从使用中排除的端口。

  - 值范围： **0** - **65535**  
    例如， **5984** 表示单个端口， **5000–5100** 表示一组端口。 如果任何值超出 0 **到 **65535** 的范围**，或者无法解释任何值，则 RPC 运行时会将整个配置视为无效。
- **PortsInternetAvailable REG\_SZ**：指定端口**值是否**表示要包含的端口或要排除的端口。

  - 值： **Y** 或 **N** （不区分大小写）
    - **Y**：端口**条目中列出的**端口表示该计算机上可用于 EPM 的所有端口。
    - **N**：端口**条目中列出的**端口表示 EPM 不可用的所有端口。
- **UseInternetPorts REG\_SZ**：指定默认系统策略。

  - 值： **Y** 或 **N** （不区分大小写）
    - **Y**：使用默认系统策略的进程是从之前定义的 Internet 可用端口集中分配的端口。
    - **N**：使用默认系统策略的进程是从仅限 Intranet 端口集分配的端口。

应打开大于端口 5000 的端口范围。 其他应用程序可能已使用小于 5000 的端口号，并打开它们进行 RPC 通信可能会导致应用程序之间的冲突。 由于多个系统服务依赖于 RPC 端口进行通信，因此至少打开 100 个端口。

注意

所需的最小端口数可能与计算机不同。 如果 RPC 动态端口受到限制，支持更多流量的计算机可能会遇到端口耗尽。 如果限制端口范围，请考虑这一点。

警告

如果在端口配置中出错，或者池中没有足够的端口，EPM 将无法注册使用动态终结点的 RPC 服务器应用程序（包括 Windows 服务（例如 Netlogon）。 如果发生配置错误，错误代码为 **87 （0x57） ERROR\_INVALID\_PARAMETER**。 例如，如果没有足够的端口，Netlogon 会记录事件 5820。 此事件的文本类似于以下示例：

```
Log Name: System  
Source: NETLOGON  
Event ID: 5820  
Level: Error  
Keywords: Classic  
Description:  
The Netlogon service could not add the AuthZ RPC interface. The service was terminated. The following error occurred: 'The parameter is incorrect.'
```

有关 RPC 工作原理的详细信息，请参阅 [通过 IT/Pro](https://techcommunity.microsoft.com/t5/ask-the-directory-services-team/rpc-over-it-pro/ba-p/399898) 的 RPC。

### 自定义端口配置示例

在此示例中，任意选择端口 5000 到 6000（含），以帮助说明如何配置新的注册表项。 此示例不是任何特定系统所需的最小端口数的建议。 此类配置需要在 HKEY\_LOCAL\_MACHINE\SOFTWARE\Microsoft\Rpc **下**添加 **Internet** 密钥，并添加以下条目：

- **端口MULTI\_SZ**
  - 数据类型： **MULTI\_SZ**
  - 值： **5000-6000**
- **PortsInternetAvailable REG\_SZ**
  - 数据类型： **REG\_SZ**
  - 值： **Y**
- **UseInternetPorts REG\_SZ**
  - 数据类型： **REG\_SZ**
  - 值： **Y**

计算机必须重启才能使此配置生效。 之后，使用 RPC 的所有应用程序都分配了 5000 到 6000 范围内的动态端口（含）。

## RPC 错误疑难解答

### PortQry

[在深入探讨网络跟踪数据之前，PortQry](https://www.microsoft.com/download/details.aspx?id=17148) 可以快速了解 RPC 的工作原理。 可以通过在客户端计算机上运行以下命令快速确定是否可以建立连接：

```
Portqry.exe -n <ServerIP> -e 135
```

注意

在此命令中， <*ServerIP*> 表示要联系的服务器 IP 地址。

例如，请考虑以下命令：

```
Portqry.exe -n 10.10.10.10 -e 135
```

此命令生成类似于以下摘录的输出：

```
Querying target system called:
10.10.10.10
Attempting to resolve IP address to a name...
IP address resolved to RPCServer.contoso.com
querying...
TCP port 135 (epmap service): LISTENING
Using ephemeral source port
Querying Endpoint Mapper Database...
Server's response:
UUID: d95afe70-a6d5-4259-822e-2c84da1ddb0d
ncacn_ip_tcp:10.10.10.10[49664]
```

通过检查此输出，可以确定以下信息：

- DNS 正常工作（它已将 IP 地址解析为完全限定的域名 （FQDN））。
- PortQry 联系了目标计算机上的 RPC 端口（135）。
- EPM 响应 PortQry，并为后续通信分配了动态端口 49664（括在方括号中）。
- PortQry 重新连接到端口 49664。

如果这些步骤中的任何一个都失败，通常可以开始收集同时的网络跟踪，如下一部分所述。

有关 PortQry 的详细信息，请参阅 [使用 PortQry 命令行工具](../../windows-server/networking/portqry-command-line-port-scanner-v2)。

### Netsh

可以使用 Windows [netsh](/zh-cn/windows-server/administration/windows-commands/netsh) 工具在客户端和服务器上同时收集网络跟踪数据。

若要收集同时的网络跟踪，请在客户端和服务器上打开提升的命令提示符窗口。

在客户端上运行以下命令：

```
Netsh trace start scenario=netconnection capture=yes tracefile=c:\client_nettrace.etl maxsize=512 overwrite=yes report=yes
```

在服务器上运行以下命令：

```
Netsh trace start scenario=netconnection capture=yes tracefile=c:\server_nettrace.etl maxsize=512 overwrite=yes report=yes
```

现在，请尝试在客户端计算机上重现问题。 然后，在两个窗口中的命令提示符处运行以下命令以停止跟踪：

```
Netsh trace stop
```

在 [Microsoft网络监视器 3.4](collect-data-using-network-monitor) 或消息分析器中打开跟踪文件。 筛选服务器或客户端计算机和 TCP 端口 135 的 IP 地址的跟踪数据。 例如，使用筛选器字符串，例如以下示例：

- `Ipv4.address==<client-ip> and ipv4.address==<server-ip> and tcp.port==135`

  注意

  在此筛选器字符串中， <client-ip> 表示客户端的 IP 地址， <服务器 IP> 表示服务器的 IP 地址。
- `tcp.port==135`

在筛选的数据中**，在“协议**”列中查找 **EPM** 条目。

查找 EPM（在服务器上）包含动态端口号的响应。 如果存在动态端口号，请记下它以供将来参考。

![“网络监视器”的屏幕截图，其中突出显示了动态端口。](media/rpc-errors-troubleshooting/dynamic-port-number.png)

重新生成动态端口号和服务器 IP 地址的跟踪数据。 例如，使用筛选器字符串，例如 **tcp.port==*<dynamic-port-allocated*> 和 ipv4.address==*<server-ip。*>** 在此筛选器字符串中，<*动态端口分配*>表示动态端口号，*<服务器 IP*> 表示服务器的 IP 地址。

![应用了筛选器的网络监视器的屏幕截图。](media/rpc-errors-troubleshooting/filtered-trace.png)

在筛选的数据中，查找客户端成功连接到动态端口的证据，或查找可能出现的任何网络问题。

### 不可访问的端口

“RPC 服务器不可用”错误的最常见原因是客户端无法连接到已分配的动态端口。 然后，客户端跟踪会显示动态端口的 TCP SYN 重新传输。

![显示 TCP SYN 重新传输的网络监视器的屏幕截图。](media/rpc-errors-troubleshooting/tcp-syn-retransmit.png)

此行为指示以下条件之一正在阻止通信：

- 在环境中的防火墙上阻止动态端口范围。
- 中间设备正在删除数据包。
- 目标服务器正在删除数据包。 这种情况可能是由 Windows 筛选平台（WFP）数据包丢弃、网络接口卡（NIC）数据包丢弃或筛选器驱动程序[修改等](/zh-cn/windows-hardware/drivers/network/sending-data-from-a-filter-driver)[配置](/zh-cn/windows/security/threat-protection/auditing/audit-filtering-platform-packet-drop)引起的。

## 收集数据以便进行更深入的故障排除

在联系Microsoft支持人员之前，建议收集有关问题的信息。

### 先决条件

这些过程使用 [TroubleShootingScript （TSS）](../windows-troubleshooters/introduction-to-troubleshootingscript-toolset-tss) 工具集。 若要使用此工具集，应注意以下先决条件：

- 你必须对本地计算机具有管理员级权限。
- 首次运行工具集时，必须接受 EULA。
- 确保将计算机的 Windows PowerShell 脚本执行策略设置为 `RemoteSigned`。 有关 PowerShell 执行策略的详细信息，请参阅 [about\_Execution\_Policies](/zh-cn/powershell/module/microsoft.powershell.core/about/about_execution_policies)。

  注意

  如果环境阻止在计算机级别使用 `RemoteSigned` ，则可以在进程级别临时设置它。 为此，请在提升的 PowerShell 命令提示符窗口中运行以下 cmdlet，然后再启动该工具：

  ```
  PS C:\> Set-ExecutionPolicy -scope Process -ExecutionPolicy RemoteSigned
  ```

  若要验证更改是否生效，请运行 `PS C:\> Get-ExecutionPolicy -List` cmdlet。

  进程级权限仅适用于当前的 PowerShell 会话。 关闭 PowerShell 窗口后，执行策略将还原为原始设置。

### 在联系Microsoft支持人员之前收集关键信息

1. 在所有节点上下载 [TSS](https://aka.ms/getTSS) ，并将其展开到 *C：\tss* 文件夹。
2. 在 *提升的 PowerShell 命令提示符窗口中打开 C：\tss* 文件夹。
3. 通过运行以下 cmdlet 在问题计算机上启动跟踪：

   ```
   .\TSS.ps1 -Scenario NET_RPC
   ```
4. 响应 EULA 提示符。
5. 重现此问题。 可以使用 事件查看器 或 [wbemtest](/zh-cn/mem/configmgr/develop/core/understand/introduction-to-wbemtest) 等工具来监视或测试问题。
6. 重现问题后，立即停止收集数据。
7. 在自动化脚本完成收集所需数据后，将数据附加到支持请求。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/rpc-errors-troubleshooting)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
