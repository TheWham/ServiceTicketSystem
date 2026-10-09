# 影响 Microsoft Entra Connect 的 RPC 错误

## 概要

客户可能会遇到无法配置 Microsoft Entra Connect 的问题，或者由于远程过程调用（RPC）相关的错误启用功能。

客户可能还会体验以前启用的功能由于这些类型的错误而停止工作。

在绝大多数情况下，此问题会影响 Microsoft Entra Connect，而不是由 Microsoft Entra Connect 引起的，因此找到确切的基础问题对于正确定义故障排除步骤并识别导致错误的正确基础问题至关重要。

本文介绍受 RPC 错误影响的 Microsoft Entra Connect 功能的示例。

## 调查影响 Microsoft Entra Connect 的远程过程调用错误

识别问题时，通常建议在排查初始步骤时使用事件查看器仔细调查应用程序事件。 确定从远程过程调用返回的系统错误将帮助你确定调查的目标，并定义正确的故障排除方法和工具。

对于这些类型的错误，应用程序事件包括有关 RPC 错误的信息，如以下示例所示：

### 示例 1

[![屏幕截图显示应用程序事件包括有关 R P C 错误 1722 的信息。](media/rpc-errors-aadconnect/rpc-error-1722.png)](media/rpc-errors-aadconnect/rpc-error-1722.png#lightbox)

上图中显示的应用程序错误事件的代码片段：

```
Log Name:      Application
Source:        Directory Synchronization
Date:          8/10/2020 11:00:39 AM
Event ID:      611
Task Category: None
Level:         Error
Keywords:      Classic
User:          N/A
Computer:      server1.contoso.com
Description:   Password hash synchronization failed for domain: contoso.com, domain controller hostname: <not available>, domain controller IP address: <not available>.
Details:       Microsoft.Online.PasswordSynchronization.SynchronizationManagerException: Unable to open connection to domain: contoso.com. Error: There was an error establishing a connection to the directory replication service. Domain controller hostname: server1.contoso.com, domain controller IP address: 10.0.0.202 ---> Microsoft.Online.PasswordSynchronization.DirectoryReplicationServices.DrsCommunicationException: There was an error establishing a connection to the directory replication service. Domain controller hostname: server1.contoso.com, domain controller IP address: 10.0.0.202 ---> Microsoft.Online.PasswordSynchronization.DirectoryReplicationServices.
DrsException:  There was an error creating the connection context. ---> Microsoft.Online.PasswordSynchronization.DirectoryReplicationServices.DrsCommunicationException: RPC Error 1722 : The RPC server is unavailable. Error creating the RPC binding handle
```

在这种情况下，RPC 通信失败，出现错误**“1722：RPC 服务器不可用”。**

[系统错误代码 1700-3999](/zh-cn/windows/win32/debug/system-error-codes--1700-3999-)

在此示例中，此错误影响 Microsoft Entra Connect 密码同步功能。

### 故障排除示例 1

示例 1 中的错误是常见的网络相关错误，可在排查 TCP/IP RPC 错误[时](/zh-cn/windows/client-management/troubleshoot-tcpip-rpc-errors)找到故障排除步骤。

在此方案中，调查网络跟踪显示重新传输数据包以与目标 **端口 135** 通信，因此此端口上的流量在目标服务器上被阻止。

[![屏幕截图显示目标服务器上正在阻止流量。](media/rpc-errors-aadconnect/traffic-block.png)](media/rpc-errors-aadconnect/traffic-block.png#lightbox)

这些错误可能会间歇性地出现，这增加了收集数据（如网络跟踪）的复杂性，以便进行调查和故障排除。

以下步骤允许在生成错误事件 ID 时自动收集网络跟踪。

注意

若要自动收集网络跟踪， **Microsoft必须在 Microsoft Entra Connect 服务器上安装网络监视器** 。

[下载 Netmon](https://www.microsoft.com/download/details.aspx?id=4865)

1. 在提升的命令提示符下运行以下命令：

   ```
   nmcap /network * /Capture /file c:\MSData\%Computername%_Trace.cap:500M /StopWhen /Frame (ICMP and Ipv4.TotalLength == 328) /CaptureProcesses /TimeAfter 2s
   ```
2. 若要在生成错误时停止跟踪，请发送大小正确的 Ping。

   在脚本（例如 cmd 文件）中准备 Ping 命令，该脚本是在Microsoft Entra Connect 在事件日志中引发错误时执行的。

   Ping 命令：

   ```
   ping -l 300 -n 2 1.2.3.4
   ```
3. 将运行在上一步中创建的 cmd 文件的任务附加到问题重现时生成的事件。 这将触发停止跟踪的 ping 命令。

   ![用于将运行上一步骤中创建的 cmd 文件的任务附加到事件的屏幕截图。](media/rpc-errors-aadconnect/attach-task.png)

### 示例 2

![屏幕截图显示应用程序事件包括有关 R P C 错误 8333 的信息。](media/rpc-errors-aadconnect/rpc-error-8333.png)

上图中显示的应用程序错误事件的代码片段：

```
Log Name:      Application
Source:        Directory Synchronization
Date:          8/3/2020 8:17:55 PM
Event ID:      611
Task Category: None
Level:         Error
Keywords:      Classic
User:          N/A
Computer:      server1.contoso.com
Description:   Password hash synchronization failed for domain: contoso.com, domain controller hostname: server1.contoso.com, domain controller IP address: 192.168.0.0.
Details:       Microsoft.Online.PasswordSynchronization.SynchronizationManagerException: Recovery task failed. ---> Microsoft.Online.PasswordSynchronization.DirectoryReplicationServices.
DrsException:  RPC Error 8333 : Directory object not found. There was an error calling _IDL_DRSGetNCChanges.
```

其他基础结构配置问题可能会导致远程过程调用问题，例如 DNS 名称解析、身份验证问题等。

请务必注意错误号，以便进行适当的调查和故障排除。

### 故障排除示例 2

在示例 2 中，远程过程调用返回的错误为 **8333**，“找不到目录对象”的错误

[系统错误代码 8200-8999](/zh-cn/windows/win32/debug/system-error-codes--8200-8999-)

Microsoft Entra Connect 服务器找不到尝试在 Active Directory 中执行密码哈希同步的用户对象。

有关更多详细信息和故障排除指南，请参阅 [Windows Server 故障排除：RPC 服务器不可用](https://social.technet.microsoft.com/wiki/contents/articles/4494.windows-server-troubleshooting-rpc-server-is-unavailable.aspx)。

### 示例 3

![屏幕截图显示密码设置操作期间发生意外错误。](media/rpc-errors-aadconnect/error-failed-0x6ba.png)

上图中显示的应用程序错误事件的代码片段：

```
Log Name:      Application
Source:        ADSync
Date:          7/28/2020 7:07:20 PM
Event ID:      6329
Task Category: Server
Level:         Error
Keywords:      Classic
User:          N/A
Computer:      server1.contoso.com
Description:   An unexpected error has occurred during a password set operation.
"BAIL: MMS(4984): ..\dnutils.cpp(1341): 0x800700b7 (Cannot create a file when that file already exists.)
ERR_: MMS(4984): X:\bt\1016372\repo\src\dev\sync\ma\shared\inc\MAUtils.h(58): Failed getting registry value 'ADMADoNormalization', 0x2
BAIL: MMS(4984): X:\bt\1016372\repo\src\dev\sync\ma\shared\inc\MAUtils.h(59): 0x80070002 (The system cannot find the file specified.): Win32 API failure: 2
BAIL: MMS(4984): X:\bt\1016372\repo\src\dev\sync\ma\shared\inc\MAUtils.h(114): 0x80070002 (The system cannot find the file specified.)
ERR_: MMS(4984): X:\bt\1016372\repo\src\dev\sync\ma\shared\inc\MAUtils.h(58): Failed getting registry value 'ADMARecursiveUserDelete', 0x2
BAIL: MMS(4984): X:\bt\1016372\repo\src\dev\sync\ma\shared\inc\MAUtils.h(59): 0x80070002 (The system cannot find the file specified.): Win32 API failure: 2
BAIL: MMS(4984): X:\bt\1016372\repo\src\dev\sync\ma\shared\inc\MAUtils.h(114): 0x80070002 (The system cannot find the file specified.)
ERR_: MMS(4984): X:\bt\1016372\repo\src\dev\sync\ma\shared\inc\MAUtils.h(58): Failed getting registry value 'ADMARecursiveComputerDelete', 0x2
BAIL: MMS(4984): X:\bt\1016372\repo\src\dev\sync\ma\shared\inc\MAUtils.h(59): 0x80070002 (The system cannot find the file specified.): Win32 API failure: 2
BAIL: MMS(4984): X:\bt\1016372\repo\src\dev\sync\ma\shared\inc\MAUtils.h(114): 0x80070002 (The system cannot find the file specified.)
ERR_: MMS(4984): admaexport.cpp(2939): Failed to acquire user information: 0x6ba
BAIL: MMS(4984): admaexport.cpp(2963): 0x80004005 (Unspecified error)
BAIL: MMS(4984): admaexport.cpp(3296): 0x80004005 (Unspecified error)
ERR_: MMS(4984): ..\ma.cpp(8000): ExportPasswordSet failed with 0x80004005
Azure AD Sync 1.4.18.0"
```

请务必知道错误可以在十六进制代码中表示，如此示例所示。

还可以使用十六进制错误代码搜索错误符号名称。

错误 **“0x6ba”** 转换为 **“RPC 服务器不可用”错误 1722**。 示例 1 **中使用的**故障排除步骤也适用于此处。

[系统错误代码 1700-3999](/zh-cn/windows/win32/debug/system-error-codes--1700-3999-)

### 示例 4

另一个以十六进制形式表示的 RPC 错误的示例：

![屏幕截图显示了以十六进制形式表示的 R P C 错误的示例。](media/rpc-errors-aadconnect/error-failed-0x5.png)

在这种情况下，返回 **“0x5”** 的错误转换为拒绝访问错误：

[系统错误代码 0-499](/zh-cn/windows/win32/debug/system-error-codes--0-499-)

引发访问被拒绝错误的原因可能有多种。 强化 Active Directory 中实现的组策略是其中之一。 一个示例是限制允许对 SAM 进行调用的客户端：

[网络访问：限制允许远程调用 SAM 的客户端](/zh-cn/windows/security/threat-protection/security-policy-settings/network-access-restrict-clients-allowed-to-make-remote-sam-calls)

## 影响 Microsoft Entra Connect 的远程过程调用中返回的其他常见系统错误代码

| 错误 ID | 十六进制错误表示形式 | 错误符号名称 | 错误描述性文本 |
| --- | --- | --- | --- |
| [1127](/zh-cn/windows/win32/debug/system-error-codes--1000-1299-) | 0x467 | ERROR\_DISK\_OPERATION\_FAILED | 访问硬盘时，即使重试，磁盘操作也会失败。 |
| [1130](/zh-cn/windows/win32/debug/system-error-codes--1000-1299-) | 0x46A | ERROR\_NOT\_ENOUGH\_SERVER\_MEMORY | 服务器存储空间不足，无法处理此命令。 |
| [1331](/zh-cn/windows/win32/debug/system-error-codes--1300-1699-) | 0x533 | ERROR\_ACCOUNT\_DISABLED | 此用户无法登录，因为此帐户当前已禁用。 |
| [14](/zh-cn/windows/win32/debug/system-error-codes--0-499-) | 0xE | ERROR\_OUTOFMEMORY | 没有足够的存储空间来完成此操作。 |
| [1450](/zh-cn/windows/win32/debug/system-error-codes--1300-1699-) | 0x5AA | ERROR\_NO\_SYSTEM\_RESOURCES | 系统资源不足，无法完成请求的服务。 |
| [1722](/zh-cn/windows/win32/debug/system-error-codes--1700-3999-) | 0x6BA | RPC\_S\_SERVER\_UNAVAILABLE | RPC 服务器不可用。 |
| [1723](/zh-cn/windows/win32/debug/system-error-codes--1700-3999-) | 0x6BB | RPC\_S\_SERVER\_TOO\_BUSY | RPC 服务器太忙，无法完成此操作。 |
| [1726](/zh-cn/windows/win32/debug/system-error-codes--1700-3999-) | 0x6BE | RPC\_S\_CALL\_FAILED | 远程过程调用失败。 |
| [1727](/zh-cn/windows/win32/debug/system-error-codes--1700-3999-) | 0x6BF | RPC\_S\_CALL\_FAILED\_DNE | 远程过程调用失败，未执行。 |
| [1728](/zh-cn/windows/win32/debug/system-error-codes--1700-3999-) | 0x6C0 | RPC\_S\_PROTOCOL\_ERROR | 发生了远程过程调用 （RPC） 协议错误。 |
| [1753](/zh-cn/windows/win32/debug/system-error-codes--1700-3999-) | 0x6D9 | EPT\_S\_NOT\_REGISTERED | 端点映射程序中未提供更多端点。 |
| [1818](/zh-cn/windows/win32/debug/system-error-codes--1700-3999-) | 0x71A | RPC\_S\_CALL\_CANCELLED | 远程过程调用已取消。 |
| [1825](/zh-cn/windows/win32/debug/system-error-codes--1700-3999-) | 0x721 | RPC\_S\_SEC\_PKG\_ERROR | 发生了特定于安全包的错误。 |
| [5](/zh-cn/windows/win32/debug/system-error-codes--0-499-) | 0x5 | ERROR\_ACCESS\_DENIED | 拒绝访问。 |
| [6](/zh-cn/windows/win32/debug/system-error-codes--0-499-) | 0x6 | ERROR\_INVALID\_HANDLE | 句柄 无效。 |
| [8333](/zh-cn/windows/win32/debug/system-error-codes--8200-8999-) | 0x208D | ERROR\_DS\_OBJ\_NOT\_FOUND | 找不到目录对象。 |
| [8420](/zh-cn/windows/win32/debug/system-error-codes--8200-8999-) | 0x20E4 | ERROR\_DS\_CANT\_FIND\_EXPECTED\_NC | 找不到命名上下文。 |
| [8439](/zh-cn/windows/win32/debug/system-error-codes--8200-8999-) | 0x20F7 | ERROR\_DS\_DRA\_BAD\_DN | 为此复制操作指定的可分辨名称无效。 |
| [8446](/zh-cn/windows/win32/debug/system-error-codes--8200-8999-) | 0x20FE | ERROR\_DS\_DRA\_OUT\_OF\_MEM | 复制操作未能分配内存。 |
| [8451](/zh-cn/windows/win32/debug/system-error-codes--8200-8999-) | 0x2103 | ERROR\_DS\_DRA\_DB\_ERROR | 复制操作遇到数据库错误。 |
| [8453](/zh-cn/windows/win32/debug/system-error-codes--8200-8999-) | 0x2105 | ERROR\_DS\_DRA\_ACCESS\_DENIED | 复制访问被拒绝。 |
| [8456](/zh-cn/windows/win32/debug/system-error-codes--8200-8999-) | 0x2108 | ERROR\_DS\_DRA\_SOURCE\_DISABLED | 源服务器当前拒绝复制请求。 |
| [8465](/zh-cn/windows/win32/debug/system-error-codes--8200-8999-) | 0x2111 | ERROR\_DS\_DRA\_SOURCE\_IS\_PARTIAL\_REPLICA | 复制同步尝试失败，因为主副本尝试从部分副本同步。 |

## 详细信息

可以通过 [错误代码找到系统错误代码](/zh-cn/windows/win32/debug/system-error-codes)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/rpc-errors-affecting-aadconnect)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
