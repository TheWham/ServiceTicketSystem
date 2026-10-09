# 排查适用于 Windows 的全局安全访问客户端中的问题

## 总结

[全局安全访问客户端](/zh-cn/entra/global-secure-access/how-to-install-windows-client)部署在托管Microsoft Windows 设备上（即Microsoft Entra 混合加入设备或已加入 Microsoft Entra 的设备）。 它使组织能够控制这些设备与 Internet 或 Intranet（本地公司网络）上可用的各种网站、应用程序和资源之间的网络流量。 如果使用此方法路由流量，可以强制实施并应用更多检查和控制，例如持续访问评估（CAE）、设备符合性和多重身份验证，以便进行资源访问。

[![通过 Microsoft Entra 路由来自全局安全访问客户端的流量到 Internet 或 Intranet 的访问的示意图。](media/troubleshoot-global-secure-access-client-windows-issues/global-secure-access-architecture.png)](media/troubleshoot-global-secure-access-client-windows-issues/global-secure-access-architecture.png#lightbox)

## 安装

使用以下方法在托管 Windows 设备上安装全局安全访问客户端：

- 以本地管理员身份在 Windows 设备上下载并安装。
- 通过使用组策略对 Microsoft Entra 混合加入设备进行 Active Directory 域服务（AD DS）部署。
- 通过 Intune 或其他 MDM 服务部署Microsoft Entra 混合联接或Microsoft已加入 Entra 的设备。

如果在尝试安装全局安全访问客户端时遇到故障，请检查以下各项：

- [适用于 Windows 的全局安全访问客户端的先决条件](/zh-cn/entra/global-secure-access/how-to-install-windows-client#prerequisites)
- 全局安全访问客户端日志中的错误（*C：\Users\<username>\AppData\Local\Temp\Global\_Secure\_Access\_Client\_<number>.log*）
- 任何其他错误（例如进程失败）的应用程序和系统事件日志

如果尝试升级客户端时遇到问题，请先尝试卸载早期客户端版本并重启设备，然后重试安装升级。

## 安装后问题的自助服务诊断工具

在安装成功后，使用以下自助服务诊断工具来排查全局安全访问客户端中的问题：

- [**对全球安全访问客户端进行故障排除：高级诊断**](/zh-cn/entra/global-secure-access/troubleshoot-global-secure-access-client-advanced-diagnostics)
- [**对全球安全访问客户端进行故障排除：“运行状况检查”选项卡**](/zh-cn/entra/global-secure-access/troubleshoot-global-secure-access-client-diagnostics-health-check)

如果诊断工具无法解决问题，[请收集故障排除日志](/zh-cn/entra/global-secure-access/troubleshoot-global-secure-access-client-advanced-diagnostics?branch=main#advanced-log-collection-tab)，然后附上日志提交支持请求。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/global-secure-access/troubleshoot-global-secure-access-client-windows-issues)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
