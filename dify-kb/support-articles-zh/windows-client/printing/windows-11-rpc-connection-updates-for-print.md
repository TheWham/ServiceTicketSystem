# Windows 11 中打印的 RPC 连接更新

*适用于：* Windows 11 版本 22H2 及更高版本的 Windows

Windows 11 版本 22H2 引入了对打印组件所做的更改，这些组件可修改 Windows 计算机在打印或打印相关操作期间相互通信的方式。
例如，当打印到由打印服务器或网络上的其他计算机共享的打印机时，更改将生效。 进行了这些更改，以进一步提高 Windows 中打印的整体安全性。
RPC 连接设置的默认配置强制执行更新且更安全的通信方法。 家庭用户和企业管理员可以自定义其环境的设置。

## 更新详细信息

- 对于打印相关的通信，默认情况下，RPC over TCP 用于客户端 - 服务器通信。

  - 使用 RPC over Named Pipes 在计算机之间打印相关的通信仍然可用，但默认处于禁用状态。
  - 可以通过组策略或注册表控制通过命名管道通过 TCP 或 RPC 进行打印相关通信。
- 默认情况下，客户端或服务器仅通过 TCP 通过 RPC 侦听传入连接。

  - 可以将后台处理程序服务配置为还可以通过命名管道通过 RPC 侦听传入连接。 这不是默认配置。
  - 此行为可由组策略或注册表控制。
- 使用 RPC over TCP 时，可以将特定端口配置为用于通信，而不是动态端口。
- 所有计算机都加入域并支持 Kerberos 的环境现在可以强制实施 Kerberos 身份验证。

## 有关配置环境的建议

下面包含有关如何正确配置环境的建议，以避免或解决计算机之间的通信问题。

### 允许通过 TCP 通信进行 RPC

最常见的问题是防火墙规则阻止计算机之间的通信。 若要解决防火墙问题，请执行以下步骤：

1. 确保未阻止 RPC 终结点映射器端口（135）。
2. 在服务器上打开高范围临时端口（49152 – 65535），或按照下面的“配置 RPC 以使用某些端口[”部分的](#configuring-rpc-to-use-certain-ports)指南指定 RPC 的端口范围。

有关不同端口及其按系统服务使用的详细信息，请参阅 [Windows](../../windows-server/networking/service-overview-and-network-port-requirements) 的服务概述和网络端口要求。

### 通过命名管道使用 RPC

不建议使用此配置。 但是，如果 RPC over TCP 不是当前环境中的选项，则可以使用它。

- 若要启用 Windows 11 版本 22H2 计算机以通过命名管道使用 RPC 而不是通过 TCP 进行 RPC 进行通信，请参阅“ [通过命名管道使用 RPC 进行客户端 - 服务器通信](#use-rpc-over-named-pipes-for-client--server-communication) ”部分。
- 若要启用 Windows 11 版本 22H2 计算机以通过命名管道通过 RPC 侦听传入连接，并通过 TCP 通过 RPC 侦听 RPC，请参阅“ [通过命名管道](#enable-listening-for-incoming-connections-on-rpc-over-named-pipes) 侦听 RPC 上的传入连接”部分

还需要以下附加配置才能在环境中正确支持基于命名管道的 RPC。

- 将 **RpcAuthnLevelPrivacyEnabled** 注册表值设置为 **服务器/主机计算机上的 0** 。 请参阅 [管理 CVE-2021-1678（KB4599464） 的打印机 RPC 绑定更改的部署（microsoft.com）](https://support.microsoft.com/topic/managing-deployment-of-printer-rpc-binding-changes-for-cve-2021-1678-kb4599464-12a69652-30b9-3d61-d9f7-7201623a8b25)
- 某些方案还需要 SMB2/SMB3 中的来宾访问，默认情况下禁用。 若要启用它，请参阅 [如何在 SMB2 和 SMB3](/zh-cn/windows-server/storage/file-server/enable-insecure-guest-logons-smb2-and-smb3) 中启用不安全的来宾登录。

## 将 RPC 配置为使用某些端口

请参阅 [如何配置 RPC 以使用某些端口，以及如何使用 IPsec](https://support.microsoft.com/topic/how-to-configure-rpc-to-use-certain-ports-and-how-to-help-secure-those-ports-by-using-ipsec-2a94b798-063a-479a-8452-9cf07ac613d9) 帮助保护这些端口。

- 若要设置动态/排除端口范围，请运行 `netsh int` 命令。
- 若要将 IPSec 与 netsh 配合使用，请运行 `netsh ipsec` 命令。
- 若要使用 Windows 防火墙阻止一系列端口，请运行 `netsh advfirewall` 命令。

上述所有解决方案都是可行的解决方案。 但是，某些解决方案可能比要求为每个端口设置规则（IPSec 和 AdvFirewall）更轻松。 出于测试目的，可以使用动态/排除端口范围方法，因为可以指定范围。 例如：

若要限制动态端口范围，请运行以下命令：

```
netsh int ipv4 show dynamicport tcp
netsh int ipv4 show dynamicport udp
netsh int ipv4 set dynamicportrange tcp startport=50000 numberofports=255
netsh int ipv4 set dynamicportrange udp startport=50000 numberofports=255
netsh int ipv6 set dynamicportrange tcp startport=50000 numberofports=255
netsh int ipv6 set dynamicportrange udp startport=50000 numberofports=255
```

然后重启计算机。

注意

255 是可以设置的最小端口数。

若要进一步限制端口范围，请运行以下命令：

```
netsh int ip show excludedportrange tcp
netsh int ip show excludedportrange udp
netsh int ipv4 add excludedportrange tcp startport=50000 numberofports=225
netsh int ipv4 add excludedportrange udp startport=50000 numberofports=225
netsh int ipv6 add excludedportrange tcp startport=50000 numberofports=225
netsh int ipv6 add excludedportrange udp startport=50000 numberofports=225
```

然后重启计算机。

注意

如果限制端口数量过多，则系统上的服务将无法有效通信，并可能导致功能出现问题。

## 为 Windows 打印组件配置 RPC 通信

可以通过组策略或直接通过注册表配置以下设置，以实现所需的效果。 有关每个设置的特定详细信息，请参阅组策略编辑器中的文档。

### 通过命名管道使用 RPC 进行客户端 – 服务器通信

- 使用组策略启用：  
  路径：**计算机配置****>管理模板**>**打印机**>**配置 RPC 连接设置**  
  启用并设置为 **RpcOverNamedPipes**。
- 使用注册表启用设置：  
  `reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows NT\Printers\RPC" /v RpcUseNamedPipeProtocol /t REG_DWORD /d 1 /f`运行

### 启用通过命名管道侦听 RPC 上的传入连接

- 通过组策略启用：  
  路径：计算机配置 > 管理模板 > 打印机 > 配置 RPC 侦听器设置  
  启用和设置允许用于 **RpcOverNamedPipesAndTcp** 的协议。
- 通过注册表启用设置：  
  `reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows NT\Printers\RPC" /v RpcProtocols /t REG_DWORD /d 0x7 /f`运行

### 通过 TCP 通信使用特定端口进行 RPC

- 通过组策略启用：  
  路径：**计算机配置****>管理模板****>打印机**>**通过 TCP 端口**配置 RPC 启用并设置端口号
- 通过注册表启用设置  
  `reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows NT\Printers\RPC" /v RpcTcpPort /t REG_DWORD /d <port number> /f`运行

最大端口：65535

### 强制实施 Kerberos 身份验证

- 通过组策略启用：  
  路径：**计算机配置****>管理模板**>**打印机**>**配置 RPC 侦听器设置**  
  启用和设置允许用于 Kerberos 的身份验证协议。
- 通过注册表启用设置  
  `reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows NT\Printers\RPC" /v ForceKerberosForRpc /t REG_DWORD /d 1 /f`运行

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/windows-11-rpc-connection-updates-for-print)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
