# 802.1X 身份验证高级排查

_适用于：_ &nbsp; Windows 10

## 概述

本文介绍 802.1X 无线和有线客户端的一般性排查方法。排查 802.1X 和无线问题时，关键在于先弄清身份验证的流程，然后找出流程在哪一环中断。这一过程涉及许多第三方设备和软件——多数情况下，我们负责定位问题所在，再由其他厂商负责修复，因为接入点或交换机并不是端到端的 Microsoft 解决方案。

## 适用场景

本排查方法适用于任何尝试使用 802.1X 身份验证建立无线或有线连接但失败的场景。工作流程涵盖 Windows 7 到 Windows 10（及 Windows 11）客户端，以及 Windows Server 2008 R2 到 Windows Server 2012 R2 上的 NPS。

## 已知问题

无

## 数据收集

请参阅 [802.1X 身份验证排查数据收集](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/data-collection-for-troubleshooting-802-1x-authentication-issues)。

## 排查方法

在 Windows 安全事件日志中查看 NPS 身份验证状态事件，是获取身份验证失败信息最有用的排查方法之一。

NPS 事件日志条目包含连接尝试的信息，包括与连接尝试匹配的连接请求策略名称，以及接受或拒绝连接尝试的网络策略。如果你未能同时看到成功和失败两类事件，请参阅本文后面的 [NPS 审核策略](#审核策略) 一节。

在 NPS 服务器的 Windows 安全事件日志中检查 NPS 事件：连接尝试被拒绝对应事件 ID 6273，被接受对应事件 ID 6272。

在事件消息中滚动到最下方，检查"Reason Code"（原因代码）字段及其关联文本。

WLAN AutoConfig 操作日志（Operational log）会基于 WLAN AutoConfig 服务检测到或被报告的状况列出信息和错误事件。该操作日志包含无线网络适配器、无线连接配置文件的属性、指定的网络身份验证方式等信息；如果出现连接问题，还会包含失败原因。有线网络访问对应的是 Wired AutoConfig 操作日志。

在客户端上：无线问题查看 *事件查看器（本地）\\应用程序和服务日志\\Microsoft\\Windows\\WLAN-AutoConfig\\Operational*；有线网络访问问题查看 *..\\Wired-AutoConfig\\Operational*。

**大多数 802.1X 身份验证问题都源于客户端或服务器身份验证所用证书的问题**，例如证书无效、过期、证书链验证失败或吊销检查失败。

首先，确认所使用的 EAP 方法的类型。如果身份验证方法使用证书，请检查该证书是否有效。在服务器（NPS）端，可以从 EAP 属性菜单确认正在使用的证书：在 **NPS 管理单元**中，转到 **策略** > **网络策略**，右键单击策略并选择"属性"，在弹出窗口中转到 **约束**（Constraints）选项卡，然后查看"身份验证方法"部分。

CAPI2 事件日志对排查证书相关问题非常有用。该日志默认未启用。启用方法：展开 *事件查看器（本地）\\应用程序和服务日志\\Microsoft\\Windows\\CAPI2*，右键单击 **Operational**，然后选择"启用日志"。

排查复杂的 802.1X 身份验证问题时，理解 802.1X 身份验证过程非常重要。

如果你在客户端和服务器（NPS）两侧同时[收集网络数据包捕获](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/collect-data-using-network-monitor)，就能看到完整的握手流程。客户端捕获在显示筛选器中输入 *EAPOL*，NPS 端捕获输入 *EAP*。

> **备注**
> 如果你有无线跟踪数据，也可以[使用网络监视器查看 ETL 文件](/windows/desktop/ndf/using-network-monitor-to-view-etl-files)，并应用 **ONEX_MicrosoftWindowsOneX** 和 **WLAN_MicrosoftWindowsWLANAutoConfig** 网络监视器筛选器。如需加载所需的解析器（parser），请参阅网络监视器"帮助"菜单下的说明。

## 审核策略

默认情况下，NPS 用于记录连接成功和失败的审核策略（事件日志记录）是启用的。如果发现其中一种或两种记录被禁用，请按以下步骤排查。

在 NPS 服务器上运行以下命令，查看当前审核策略设置：

```console
auditpol /get /subcategory:"Network Policy Server"
```

如果成功和失败事件均已启用，输出应为：

```output
System audit policy
Category/Subcategory                      Setting
Logon/Logoff
  Network Policy Server                   Success and Failure
```

如果显示 "No auditing"，可运行以下命令启用：

```console
auditpol /set /subcategory:"Network Policy Server" /success:enable /failure:enable
```

即使审核策略看起来已完全启用，先禁用再重新启用此设置有时也有帮助。你也可以使用组策略启用网络策略服务器登录/注销审核：依次选择"计算机配置" > "策略" > "Windows 设置" > "安全设置" > "高级审核策略配置" > "审核策略" > "登录/注销" > "审核网络策略服务器"。

## 更多信息

- [Troubleshooting Windows Vista 802.11 Wireless Connections](/previous-versions/windows/it-pro/windows-vista/cc766215(v=ws.10))
- [Troubleshooting Windows Vista Secure 802.3 Wired Connections](/previous-versions/windows/it-pro/windows-vista/cc749352(v=ws.10))

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/802-1x-authentication-issues-troubleshooting)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
