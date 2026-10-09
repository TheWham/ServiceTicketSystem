# 无线网络连接的高级故障排除

[试用虚拟代理](https://vsa.services.microsoft.com/v1.0/?partnerId=7d74cf73-5217-4008-833f-87a1a278f2cb&flowId=DMC&initialQuery=31806441) - 它可以帮助你快速识别和修复常见的无线技术问题。

注意

家庭用户：本文适用于支持代理和 IT 专业人员。 有关常规故障排除，请参阅[修复Windows中的 Wi-Fi 连接问题](https://support.microsoft.com/windows/fix-wi-fi-connection-issues-in-windows-9424a1f7-6a3b-65a6-4d78-7f07eee84d2c)。

*适用于：*Windows 11和支持的 Windows 10 版本

## 概述

使用本指南诊断和解决Windows客户端 Wi-Fi 连接问题。 本指南涵盖了最常见的方案，包括缺少 Wi-Fi 适配器或控制、未显示在连接列表中的网络、失败的连接、身份验证错误、间歇性断开连接和不可靠的漫游。

本指南遵循症状优先方法。 首先确定方案、收集基线证据，然后使用 Wi-Fi 自动连接状态机和事件跟踪Windows（ETW）分析来隔离出现问题的组件和连接阶段。 本指南的末尾包含各种诊断工具输出的示例。

Important

在重置网络堆栈之前，请删除无线配置文件、删除适配器或驱动程序，或重启设备、收集基线状态并记录复制时间。 这些操作可以删除证据或暂时更改行为。

## 场景

对于以下方案，请使用本文：

- 缺少 Wi-Fi 适配器或 Wi-Fi 控件。
- Windows不显示预期的无线网络。
- 在关联或身份验证期间连接尝试失败。
- 设备已连接，但会间歇性断开。
- 访问点之间的漫游速度缓慢或不可靠。
- 此问题在操作系统、驱动程序、固件、策略、睡眠或恢复事件后启动。

注意

ETW 示例演示了用于导航无线组件事件的一般策略。 事件文本和组件行为可能因Windows版本、无线适配器、驱动程序模型、接入点和身份验证方法而异。

### 从报告的症状开始

| 症状 | 从...开始 | 要收集的证据 |
| --- | --- | --- |
| 缺少 Wi-Fi 适配器或 Wi-Fi 控件 | 确认适配器是否存在并已启用，以及 WLAN 自动配置（WlanSvc）服务是否正在运行。 如果 WlanSvc 已停止运行，Wi‑Fi 控件将被隐藏，并且 `netsh wlan` 命令会报告该服务未运行。 记录最近的操作系统、驱动程序、固件、BIOS、睡眠或唤醒方面的更改。 | 设备管理器状态、WlanSvc 服务状态、`netsh wlan show drivers``netsh wlan show interfaces`以及相关的系统事件。 |
| 未显示预期的网络 | 确认硬件和软件无线电状态、WLAN 自动配置服务状态、支持的带段以及其他客户端是否可以看到相同的网络。 | `netsh wlan show interfaces`、`netsh wlan show networks mode=bssid`以及 WLAN 自动配置操作日志。 |
| 连接或身份验证失败 | 确定在关联或身份验证期间是否发生故障。 对于企业身份验证，请使用 [高级故障排除 802.1X 身份验证](802-1x-authentication-issues-troubleshooting)。 | 无线网络报告、WLAN 自动配置操作日志、配置文件和策略详细信息以及故障时间戳。 |
| 连接断开或漫游不可靠 | 记录设备在断开连接前的时间、网络名称、接入点、信号条件以及设备是否漫游。 将客户端跟踪与接入点或控制器日志相关联。 | 无线网络报告、ETW 跟踪、适配器和驱动程序详细信息以及基础结构日志。 |
| 问题是在更新或恢复后开始出现的 | 将当前驱动程序和固件版本与设备或适配器制造商建议的版本进行比较。 在进行进一步更改之前，确定行为是否重现。 | 更新历史记录、驱动程序版本和日期、固件或 BIOS 版本、电源状态转换和 ETW 跟踪。 |
| Wi‑Fi 仍处于连接状态，但无法访问网络 | 验证 Wi-Fi 关联是否已成功完成，然后继续执行 TCP/IP、DHCP、DNS、代理或防火墙故障排除。 | IP 配置、路由、DNS 和网络连接证据。 |

### 检查已知问题和最近更改

在收集高级跟踪日志之前：

- 查看[Windows发布运行状况](/zh-cn/windows/release-health/)，了解影响已安装Windows版本的已知问题。
- 查看设备制造商的支持信息，了解无线驱动程序、固件和 BIOS 更新或已知兼容性问题。
- 记录对Windows、无线驱动程序、固件、安全软件、VPN 软件、无线配置文件、身份验证策略和接入点配置的更改。
- 如果问题影响多个客户端，请在更改客户端配置之前比较受影响的和未受影响的设备。

## 数据收集

### 收集基线信息

在提升的命令提示符下运行以下命令：

```
netsh wlan show drivers
netsh wlan show interfaces
netsh wlan show networks mode=bssid
netsh wlan show profiles
netsh wlan show wlanreport
```

该 `mode=bssid` 选项为每个可见网络添加 BSSID、信号强度、通道和无线电类型，这有助于识别带、通道和覆盖范围问题。

该 `wlanreport` 命令生成一个 HTML 报告，该报表汇总了最近的无线会话、断开连接原因、适配器信息和相关事件。 该命令在完成时显示报表位置。

另请收集以下信息：

- 每次连接尝试或断开的确切日期和时间。
- 无线适配器模型、驱动程序版本和驱动程序日期。
- Windows 版本和最近的更新历史。
- 网络名称、身份验证方法以及配置文件是否来自组策略、移动设备管理或用户。
- 来自**事件查看器**>**应用程序和服务日志**>**Microsoft**>**Windows**>**WLAN-AutoConfig**>**操作**的事件。

注意

无线报告和跟踪可以包含设备、适配器和网络标识符。 根据组织的隐私和数据处理要求处理文件。

### 收集支持诊断信息

如果你打算联系 Microsoft 支持，请使用 TroubleShootingScript (TSS) 无线场景。 下载并提取工具集，在 TSS 文件夹中打开提升的 PowerShell 会话，然后运行：

```
.\TSS.ps1 -Scenario NET_WLAN
```

第一次运行会提示你接受最终用户许可协议。 如果脚本被阻止运行，请通过运行 `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`来设置当前进程的执行策略。

有关下载说明和要求，请参阅 [TroubleShootingScript 工具集（TSS）简介](../windows-tss/introduction-to-troubleshootingscript-toolset-tss#prerequisites)。 有关其他网络场景，请参阅[收集数据以分析和排查 Windows 网络场景](../windows-tss/collect-data-analyze-troubleshoot-windows-networking-scenarios)。

### 收集 ETW 跟踪信息

对于需要高级分析的可重现问题，请在提升的命令提示符处输入以下命令。 如果输出文件夹不存在，则跟踪不会启动，因此请首先创建该文件夹：

```
if not exist c:\tmp md c:\tmp
netsh trace start wireless_dbg capture=yes overwrite=yes maxsize=4096 tracefile=c:\tmp\wireless.etl
```

注意

`wireless_dbg` 是一种旧版方案，虽然 `netsh trace show scenarios` 未将其列出，但它仍可用。 若要查看它所启用的提供程序，请运行 `netsh trace show scenario name=wireless_dbg`。 对于新的支持请求，请优先选择 TSS `NET_WLAN` 方案。

1. 重现问题并记录连接尝试或断开连接的时间。
2. 停止跟踪：

   ```
   netsh trace stop
   ```
3. 如果需要，请将跟踪转换为文本：

   ```
   netsh trace convert c:\tmp\wireless.etl
   ```

该集合会创建`wireless.cab`、`wireless.etl`，并在转换后创建`wireless.txt`。 请参阅 [ETW 捕获示例](#etw-capture-example)。

## 故障排除

下表提供了Windows中主要 Wi-Fi 组件的高级视图。

| Wi-Fi 组件 | 说明 |
| --- | --- |
| Windows 连接管理器图标。 | Windows 连接管理器（Wcmsvc）处理用户连接请求，并跨可用网络接口协调连接。 |
| WLAN 自动配置服务图标。 | WLAN 自动配置服务（WlanSvc）会扫描无线网络，并管理无线配置文件和连接。 |
| 媒体特定模块图标。 | 特定于媒体的模块（MSM）管理连接安全性、关联和身份验证状态。 |
| 本机 Wi-Fi 堆栈图标。 | 本机 Wi-Fi 堆栈由与无线微型端口和用户模式 WLAN 自动配置服务交互的驱动程序和无线 API 组成。 |
| 无线微型端口图标。 | 无线微型端口驱动程序在Windows无线堆栈与适配器硬件之间通信。 |

Wi-Fi 连接状态机具有以下状态：

- 重置
- IHV\_配置
- 配置
- 关联
- 身份验证
- 已连接
- 漫游
- 等待断开连接
- 已断开连接

标准 Wi-Fi 连接倾向于在状态之间转换，例如：

- 正在连接

  重置 --> Ihv\_Configuring -- 配置 --> 关联 -->> 身份验证 --> 连接
- 正在断开连接

  已连接 --> 漫游 --> 等待断开连接 --> 断开连接 --> 重置

使用 [TextAnalysisTool](https://github.com/TextAnalysisTool/Releases) （TAT） 筛选 ETW 跟踪是一个简单的第一步，用于确定失败的连接设置在何处中断。 本文底部包含有用的 [Wi-Fi 筛选器文件](#wi-fi-filter-file-example) 。

使用**FSM 状态转换**跟踪过滤器来查看连接状态机。 你可以在此页面底部的 TAT 中看到[此筛选器的应用示例](#textanalysistool-example)。

良好的连接设置的一个示例是：

```
44676 [2]0F24.1020::‎2018‎-‎09‎-‎17 10:22:14.658 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State: Disconnected to State: Reset
45473 [1]0F24.1020::‎2018‎-‎09‎-‎17 10:22:14.667 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State: Reset to State: Ihv_Configuring
45597 [3]0F24.1020::‎2018‎-‎09‎-‎17 10:22:14.708 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State: Ihv_Configuring to State: Configuring
46085 [2]0F24.17E0::‎2018‎-‎09‎-‎17 10:22:14.710 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State: Configuring to State: Associating
47393 [1]0F24.1020::‎2018‎-‎09‎-‎17 10:22:14.879 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State: Associating to State: Authenticating
49465 [2]0F24.17E0::‎2018‎-‎09‎-‎17 10:22:14.990 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State: Authenticating to State: Connected
```

失败的连接设置示例是：

```
44676 [2]0F24.1020::‎2018‎-‎09‎-‎17 10:22:14.658 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State: Disconnected to State: Reset
45473 [1]0F24.1020::‎2018‎-‎09‎-‎17 10:22:14.667 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State: Reset to State: Ihv_Configuring
45597 [3]0F24.1020::‎2018‎-‎09‎-‎17 10:22:14.708 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State: Ihv_Configuring to State: Configuring
46085 [2]0F24.17E0::‎2018‎-‎09‎-‎17 10:22:14.710 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State: Configuring to State: Associating
47393 [1]0F24.1020::‎2018‎-‎09‎-‎17 10:22:14.879 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State: Associating to State: Authenticating
49465 [2]0F24.17E0::‎2018‎-‎09‎-‎17 10:22:14.990 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State: Authenticating to State: Roaming
```

通过确定连接是在什么状态下失败的，您就可以更有针对性地在跟踪日志中查看最后一个已知正常状态之前的日志。

在错误状态更改之前检查 [Microsoft-Windows-WLAN-AutoConfig] 日志应显示错误的证据。 但是，错误通常通过其他无线组件传播。
在许多情况下，下一个需要关注的组件是 MSM，它位于 Wlansvc 下方。

MSM 的重要组件包括：

- 安全管理器 （SecMgr） - 处理所有连接前和连接后的安全操作。
- 身份验证引擎 （AuthMgr） - 管理 802.1x 身份验证请求

  ![显示安全管理器和身份验证管理器的 MSM 详细信息屏幕截图。](media/wireless-network-connectivity-issues-troubleshooting/msm-details.png)

其中每个组件都有自己的单独的状态机，这些状态机遵循特定的转换。
在 TextAnalysisTool 中启用 `FSM transition`、`SecMgr Transition` 和 `AuthMgr Transition` 筛选器，以查看更多详细信息。

与前面的示例更进一步，组合的筛选器如以下命令示例所示：

```
[2] 0C34.2FF0::08/28/17-13:24:28.693 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State:
Reset to State: Ihv_Configuring
[2] 0C34.2FF0::08/28/17-13:24:28.693 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State:
Ihv_Configuring to State: Configuring
[1] 0C34.2FE8::08/28/17-13:24:28.711 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State:
Configuring to State: Associating
[0] 0C34.275C::08/28/17-13:24:28.902 [Microsoft-Windows-WLAN-AutoConfig]Port[13] Peer 8A:15:14:B6:25:10 SecMgr Transition INACTIVE (1) --> ACTIVE (2)
[0] 0C34.275C::08/28/17-13:24:28.902 [Microsoft-Windows-WLAN-AutoConfig]Port[13] Peer 8A:15:14:B6:25:10 SecMgr Transition ACTIVE (2) --> START AUTH (3)
[4] 0EF8.0708::08/28/17-13:24:28.928 [Microsoft-Windows-WLAN-AutoConfig]Port (14) Peer 0x186472F64FD2 AuthMgr Transition ENABLED  --> START_AUTH
[3] 0C34.2FE8::08/28/17-13:24:28.902 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State:
Associating to State: Authenticating
[1] 0C34.275C::08/28/17-13:24:28.960 [Microsoft-Windows-WLAN-AutoConfig]Port[13] Peer 8A:15:14:B6:25:10 SecMgr Transition START AUTH (3) --> WAIT FOR AUTH SUCCESS (4)
[4] 0EF8.0708::08/28/17-13:24:28.962 [Microsoft-Windows-WLAN-AutoConfig]Port (14) Peer 0x186472F64FD2 AuthMgr Transition START_AUTH  --> AUTHENTICATING
[2] 0C34.2FF0::08/28/17-13:24:29.751 [Microsoft-Windows-WLAN-AutoConfig]Port[13] Peer 8A:15:14:B6:25:10 SecMgr Transition WAIT FOR AUTH SUCCESS (7) --> DEACTIVATE (11)
[2] 0C34.2FF0::08/28/17-13:24:29.7512788 [Microsoft-Windows-WLAN-AutoConfig]Port[13] Peer 8A:15:14:B6:25:10 SecMgr Transition DEACTIVATE (11) --> INACTIVE (1)
[2] 0C34.2FF0::08/28/17-13:24:29.7513404 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State:
Authenticating to State: Roaming
```

注意

在倒数第二行，SecMgr 切换突然失效：  
[2] 0C34.2FF0：：08/28/17-13：24：29.7512788 [Microsoft-Windows-WLAN-AutoConfig]Port[13] Peer 8A：15：14：B6：25：10 SecMgr 转换停用 （11） --> 非活动 （1）

此转换最终传播到主连接状态机，并导致身份验证阶段向漫游状态转移。 与之前一样，请重点追踪此次 SecMgr 行为发生之前的情况，以确定被停用的原因。

启用 `Microsoft-Windows-WLAN-AutoConfig` 筛选器会显示导致停用转换的更多详细信息：

```
[3] 0C34.2FE8::08/28/17-13:24:28.902 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State:
Associating to State: Authenticating
[1] 0C34.275C::08/28/17-13:24:28.960 [Microsoft-Windows-WLAN-AutoConfig]Port[13] Peer 8A:15:14:B6:25:10 SecMgr Transition START AUTH (3) --> WAIT FOR AUTH SUCCESS (4)
[4] 0EF8.0708::08/28/17-13:24:28.962 [Microsoft-Windows-WLAN-AutoConfig]Port (14) Peer 0x186472F64FD2 AuthMgr Transition START_AUTH  --> AUTHENTICATING
[0]0EF8.2EF4::‎08/28/17-13:24:29.549 [Microsoft-Windows-WLAN-AutoConfig]Received Security Packet: PHY_STATE_CHANGE
[0]0EF8.2EF4::08/28/17-13:24:29.549 [Microsoft-Windows-WLAN-AutoConfig]Change radio state for interface = Intel(R) Centrino(R) Ultimate-N 6300 AGN :  PHY = 3, software state = on , hardware state = off )
[0] 0EF8.1174::‎08/28/17-13:24:29.705 [Microsoft-Windows-WLAN-AutoConfig]Received Security Packet: PORT_DOWN
[0] 0EF8.1174::‎08/28/17-13:24:29.705 [Microsoft-Windows-WLAN-AutoConfig]FSM Current state Authenticating , event Upcall_Port_Down
[0] 0EF8.1174:: 08/28/17-13:24:29.705 [Microsoft-Windows-WLAN-AutoConfig]Received IHV PORT DOWN, peer 0x186472F64FD2
[2] 0C34.2FF0::08/28/17-13:24:29.751 [Microsoft-Windows-WLAN-AutoConfig]Port[13] Peer 8A:15:14:B6:25:10 SecMgr Transition WAIT FOR AUTH SUCCESS (7) --> DEACTIVATE (11)
 [2] 0C34.2FF0::08/28/17-13:24:29.7512788 [Microsoft-Windows-WLAN-AutoConfig]Port[13] Peer 8A:15:14:B6:25:10 SecMgr Transition DEACTIVATE (11) --> INACTIVE (1)
[2] 0C34.2FF0::08/28/17-13:24:29.7513404 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State:
Authenticating to State: Roaming
```

向后回溯可见端口断开通知：

[0] 0EF8.1174:: 08/28/17-13:24:29.705 [Microsoft-Windows-WLAN-AutoConfig]收到 IHV 端口关闭事件，对等方 0x186472F64FD2

端口事件表明发生在更接近无线硬件层面的变化。 你可以继续查看此指示的来源，以追溯这条线索。

从 MSM 继续，Native Wi-Fi 堆栈将请求传递给无线微型端口驱动程序。 堆栈以以太网（802.3）接口的形式向 TCP/IP 和其他协议提供无线适配器，因此 802.11 帧在到达协议堆栈之前，会将 802.3 帧转换为 802.3 数据包。

注意

`[Microsoft-Windows-NWiFi]`此示例中的事件来自旧版 Native 802.11 微型端口驱动程序模型。 当前适配器使用 WLAN 设备驱动程序接口（WDI），或者在Windows 11上使用 Wi-Fi 类扩展（WiFiCx）驱动程序模型。 连接阶段是等效的，但驱动程序级事件名称和提供程序详细信息不同。

为 `[Microsoft-Windows-NWifi]` 启用跟踪筛选器：

```
[3] 0C34.2FE8::08/28/17-13:24:28.902 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State:
Associating to State: Authenticating
[1] 0C34.275C::08/28/17-13:24:28.960 [Microsoft-Windows-WLAN-AutoConfig]Port[13] Peer 8A:15:14:B6:25:10 SecMgr Transition START AUTH (3) --> WAIT FOR AUTH SUCCESS (4)
[4] 0EF8.0708::08/28/17-13:24:28.962 [Microsoft-Windows-WLAN-AutoConfig]Port (14) Peer 0x8A1514B62510 AuthMgr Transition START_AUTH  --> AUTHENTICATING
[0]0000.0000::‎08/28/17-13:24:29.127 [Microsoft-Windows-NWiFi]DisAssoc: 0x8A1514B62510 Reason: 0x4
[0]0EF8.2EF4::‎08/28/17-13:24:29.549 [Microsoft-Windows-WLAN-AutoConfig]Received Security Packet: PHY_STATE_CHANGE
[0]0EF8.2EF4::08/28/17-13:24:29.549 [Microsoft-Windows-WLAN-AutoConfig]Change radio state for interface = Intel(R) Centrino(R) Ultimate-N 6300 AGN :  PHY = 3, software state = on , hardware state = off )
[0] 0EF8.1174::‎08/28/17-13:24:29.705 [Microsoft-Windows-WLAN-AutoConfig]Received Security Packet: PORT_DOWN
[0] 0EF8.1174::‎08/28/17-13:24:29.705 [Microsoft-Windows-WLAN-AutoConfig]FSM Current state Authenticating , event Upcall_Port_Down
[0] 0EF8.1174:: 08/28/17-13:24:29.705 [Microsoft-Windows-WLAN-AutoConfig]Received IHV PORT DOWN, peer 0x186472F64FD2
[2] 0C34.2FF0::08/28/17-13:24:29.751 [Microsoft-Windows-WLAN-AutoConfig]Port[13] Peer 8A:15:14:B6:25:10 SecMgr Transition WAIT FOR AUTH SUCCESS (7) --> DEACTIVATE (11)
 [2] 0C34.2FF0::08/28/17-13:24:29.7512788 [Microsoft-Windows-WLAN-AutoConfig]Port[13] Peer 8A:15:14:B6:25:10 SecMgr Transition DEACTIVATE (11) --> INACTIVE (1)
[2] 0C34.2FF0::08/28/17-13:24:29.7513404 [Microsoft-Windows-WLAN-AutoConfig]FSM Transition from State:
Authenticating to State: Roaming
```

在跟踪信息中，你会看到这样一行：

```
[0]0000.0000::‎08/28/17-13:24:29.127 [Microsoft-Windows-NWiFi]DisAssoc: 0x8A1514B62510 Reason: 0x4
```

在位于 `PHY_STATE_CHANGE` 的接入点（AP）发送解除关联后，这一行后面会出现 `PORT_DOWN` 和 `8A:15:14:B6:25:10` 事件。

在形成理论之前解码 `Reason` 值。 该值来自 AP 发送的 IEEE 802.11 解除关联帧，因此它表明了 AP 所报告的状态。 在此示例中，`Reason: 0x4` 表示 *因不活动而解除关联*，因此调查应侧重于 AP 或控制器上的不活动计时器和会话计时器、客户端节能行为，以及客户端流量是否已停止到达 AP。 其他原因代码指示不同的条件，例如凭据无效、连接参数不兼容或不能接受更多客户端的 AP。

由于 AP 提供了原因代码，因此在更改客户端配置之前，请将其与指示的 AP 或无线控制器的日志记录相关联。

### 详细信息

- [netsh wlan](/zh-cn/windows-server/administration/windows-commands/netsh-wlan)
- [802.1X 身份验证高级故障排除](802-1x-authentication-issues-troubleshooting)
- [用于排查 802.1X 身份验证问题的数据收集](data-collection-for-troubleshooting-802-1x-authentication-issues)
- [收集数据以分析和排查 Windows 网络方案问题](../windows-tss/collect-data-analyze-troubleshoot-windows-networking-scenarios)
- [Windows 版本健康状况](/zh-cn/windows/release-health/)

## ETW 捕获示例

注意

以下捕获是说明集合输出和状态转换的历史示例。 时间戳、适配器名称和单个事件文本在当前Windows 11设备上有所不同。

```
C:\tmp>netsh trace start wireless_dbg capture=yes overwrite=yes maxsize=4096 tracefile=c:\tmp\wireless.etl

Trace configuration:
-------------------------------------------------------------------
Status:             Running
Trace File:         C:\tmp\wireless.etl
Append:             Off
Circular:           On
Max Size:           4096 MB
Report:             Off

C:\tmp>netsh trace stop
Correlating traces ... done
Merging traces ... done
Generating data collection ... done
The trace file and additional troubleshooting information have been compiled as "c:\tmp\wireless.cab".
File location = c:\tmp\wireless.etl
Tracing session was successfully stopped.

C:\tmp>netsh trace convert c:\tmp\wireless.etl

Input file:  c:\tmp\wireless.etl
Dump file:   c:\tmp\wireless.txt
Dump format: TXT
Report file: -
Generating dump ... done

C:\tmp>dir
 Volume in drive C has no label.
 Volume Serial Number is 58A8-7DE5

 Directory of C:\tmp

01/09/2019  02:59 PM    [DIR]          .
01/09/2019  02:59 PM    [DIR]          ..
01/09/2019  02:59 PM         4,855,952 wireless.cab
01/09/2019  02:56 PM         2,752,512 wireless.etl
01/09/2019  02:59 PM         2,786,540 wireless.txt
               3 File(s)     10,395,004 bytes
               2 Dir(s)  46,648,332,288 bytes free
```

## Wi-Fi 筛选器文件示例

复制并粘贴以下代码块中的所有行，并将其保存到名为 wifi.tat 的文本文件中。 通过选择 **“文件**>**加载筛选器**”将筛选器文件加载到 TextAnalysisTool 中。

```
<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<TextAnalysisTool.NET version="2018-01-03" showOnlyFilteredLines="False">
  <filters>
    <filter enabled="n" excluding="n" description="" foreColor="000000" backColor="d3d3d3" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-OneX]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Unknown]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-EapHost]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[]***" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-Winsock-AFD]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-WinHttp]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-WebIO]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-Winsock-NameResolution]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-TCPIP]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-DNS-Client]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-NlaSvc]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-Iphlpsvc-Trace]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-DHCPv6-Client]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-Dhcp-Client]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-NCSI]" />
    <filter enabled="y" excluding="n" description="" backColor="90ee90" type="matches_text" case_sensitive="n" regex="n" text="AuthMgr Transition" />
    <filter enabled="y" excluding="n" description="" foreColor="0000ff" backColor="add8e6" type="matches_text" case_sensitive="n" regex="n" text="FSM transition" />
    <filter enabled="y" excluding="n" description="" foreColor="000000" backColor="dda0dd" type="matches_text" case_sensitive="n" regex="n" text="SecMgr transition" />
    <filter enabled="y" excluding="n" description="" foreColor="000000" backColor="f08080" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-NWiFi]" />
    <filter enabled="y" excluding="n" description="" foreColor="000000" backColor="ffb6c1" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-WiFiNetworkManager]" />
    <filter enabled="y" excluding="n" description="" foreColor="000000" backColor="dda0dd" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-WLAN-AutoConfig]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-NetworkProfile]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-WFP]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[Microsoft-Windows-WinINet]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="[MSNT_SystemTrace]" />
    <filter enabled="y" excluding="y" description="" foreColor="000000" backColor="ffffff" type="matches_text" case_sensitive="n" regex="n" text="Security]Capability" />
  </filters>
</TextAnalysisTool.NET>
```

## TextAnalysisTool 示例

在以下示例中 **，视图** 设置配置为 **“仅显示筛选的行**”。

[![TextAnalysisTool 中 TAT 筛选器示例的屏幕截图。](media/wireless-network-connectivity-issues-troubleshooting/text-analysis-tool.png)](media/wireless-network-connectivity-issues-troubleshooting/text-analysis-tool.png#lightbox)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/wireless-network-connectivity-issues-troubleshooting)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
