# Microsoft Entra 混合同步代理安装问题

## 概述

这组文章中的场景描述了安装 Microsoft Entra 混合同步代理时的常见问题，以及如何纠正这些问题。

本疑难解答文档适用于为 [Microsoft Entra Connect 云同步](/azure/active-directory/cloud-sync/how-to-install)或 [Workday 自动用户预配](/azure/active-directory/saas-apps/workday-inbound-tutorial)配置代理的场景。

- [没有安装 MSI 的权限](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/azure-ad-hybrid-sync-no-privileges-install-msi)
- [无法启动服务 AADConnectProvisioningAgent](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/azure-ad-hybrid-sync-cannot-start-aadconnect-provisioning-agent)
- [gMSA 被设置为"作为服务登录"](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/azure-ad-hybrid-sync-gmsa-set-logon-service)
- [服务器上没有此对象](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/azure-ad-hybrid-sync-no-such-object-on-server)
- [由于域控制器上可能未运行 KDS，无法创建 gMSA](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/azure-ad-hybrid-sync-unable-create-gmsa-kds-domain-controller)

## 先决条件

要安装*云预配代理*，需要满足以下先决条件：[Microsoft Entra Connect 云同步的先决条件](/azure/active-directory/cloud-sync/how-to-prerequisites)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/azure-ad-hybrid-sync-agent-install-welcome)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
