# Microsoft Entra 混合同步代理安装问题 - gMSA 被设置为"作为服务登录"

本疑难解答指南重点介绍 gMSA 被设置为"作为服务登录"的情况。这种情况可能会阻止你成功安装 Microsoft Entra Connect 预配代理。

## 先决条件

要安装*云预配代理*，需要满足以下先决条件：[Microsoft Entra Connect 云同步的先决条件](/azure/active-directory/cloud-sync/how-to-prerequisites)。

## gMSA 被设置为"作为服务登录"

在安装云预配代理时，你可能会收到以下错误：

> 无法将 Windows 服务凭据更改为 gMSA。

要解决此问题，请检查系统事件日志中的 **EventID 7038**。将显示以下错误：

> 用户名或密码不正确。

打开 **Microsoft Entra Connect 预配代理**属性，选择**登录**选项卡。你会发现这些设置没有像托管服务帐户预期的那样显示为灰色。

要验证该帐户是否为托管帐户，请打开命令提示符并键入以下命令：

```console
Sc.exe qmanagedaccount aadconnectprovisioningagent
```

帐户托管状态显示为 **False**。

要将状态设置为 **True** 并解决此问题，请键入以下命令：

```console
Sc.exe managedaccount aadconnectprovisioningagent true
```

向导现在可以成功完成了。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/azure-ad-hybrid-sync-gmsa-set-logon-service)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
