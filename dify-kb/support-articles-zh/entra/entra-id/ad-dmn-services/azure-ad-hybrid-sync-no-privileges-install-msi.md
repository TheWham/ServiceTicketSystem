# Microsoft Entra 混合同步代理安装问题 - 没有安装 MSI 的权限

本疑难解答指南重点介绍没有安装 MSI 权限的情况。如果没有这些权限，你可能无法成功安装 Microsoft Entra Connect 预配代理。

## 先决条件

要安装*云预配代理*，需要满足以下先决条件：[Microsoft Entra Connect 云同步的先决条件](/azure/active-directory/cloud-sync/how-to-prerequisites)。

## 没有安装 MSI 的权限

在安装云预配代理时，你可能会收到以下错误：

> 服务"Microsoft Entra Connect Provisioning Agent"（AADConnectProvisioningAgent）启动失败。请验证你是否有足够的权限启动系统服务。

要验证你拥有足够的权限，请执行以下操作：

1. 确保用户上下文凭据设置为域管理员或企业管理员。

1. 打开本地安全策略管理单元（*secpol.msc*）。在**安全设置**窗格中，选择**本地策略** > **用户权限分配**。然后选择**作为服务登录**策略。

1. 选择**操作** > **属性**。然后在**本地安全设置**中，确保显示 `NT SERVICE\ALL SERVICES` 组。

在包安装期间，会创建 **AADConnectProvisioningAgent** 服务，并将其登录凭据临时设置为 **NT Service\AADConnectProvisioningAgent**。

如果**作为服务登录**策略中没有列出 *ALL SERVICES*，则安装将无法启动，并显示前面列出的错误消息。

要解决此问题，请为**作为服务登录**策略授予 *ALL SERVICES* 用户权限。

向导现在可以成功完成了。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/azure-ad-hybrid-sync-no-privileges-install-msi)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
