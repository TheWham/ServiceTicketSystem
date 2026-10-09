# Microsoft Entra 混合同步代理安装问题 - 无法启动服务 AADConnectProvisioningAgent

本疑难解答指南重点介绍无法启动 AADConnectProvisioningAgent 服务的情况。此问题可能会阻止你成功安装 Microsoft Entra Connect 预配代理。

## 先决条件

要安装*云预配代理*，需要满足以下先决条件：[Microsoft Entra Connect 云同步的先决条件](/azure/active-directory/cloud-sync/how-to-prerequisites)。

## 无法启动服务 AADConnectProvisioningAgent

在安装云预配代理时，你可能会收到以下错误：

> 服务"Microsoft Entra Connect Provisioning Agent"（AADConnectProvisioningAgent）启动失败。请验证你是否有足够的权限启动系统服务。

按照[如何排查代理启动失败](/azure/active-directory/cloud-sync/how-to-troubleshoot#agent-failed-to-start)中所示，为 **AADConnectProvisioningAgent** 服务分配域管理员凭据。

为服务分配凭据后，你仍可能无法完成安装向导，并收到以下错误消息：

> 无法将 Windows 服务凭据更改为 gMSA。请查看日志以获取更多详细信息。如果这无法解决此问题，请联系支持人员。

如果你在安装向导中再次选择**确认**按钮，将显示以下消息：

> 由于域控制器上可能未运行 KDS，无法创建 gMSA。请手动创建/运行 KDS。

要解决此问题，请检查系统事件日志中的 **eventID 7041**。事件详细信息描述了如何在本地安全策略管理单元（*secpol.msc*）中分配**作为服务登录**用户权限。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/azure-ad-hybrid-sync-cannot-start-aadconnect-provisioning-agent)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
