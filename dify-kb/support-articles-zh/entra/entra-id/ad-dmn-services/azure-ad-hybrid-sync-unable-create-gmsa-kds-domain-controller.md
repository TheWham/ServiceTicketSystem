# Microsoft Entra 混合同步代理安装问题 - 无法创建 gMSA，因为 KDS 可能未在域控制器上运行

本疑难解答指南侧重于介绍在多次重试后仍无法安装服务帐户的情况。 这种情况会阻止你安装 Microsoft Entra Connect 预配代理。

## 先决条件

若要安装 *云预配代理*，需要满足以下先决条件： [Microsoft Entra Connect 云同步](/zh-cn/azure/active-directory/cloud-sync/how-to-prerequisites)的先决条件。

## 无法创建 gMSA，因为 KDS 可能未在域控制器上运行

安装云预配代理时，你可能会收到以下错误：

> 无法创建 gMSA，因为 KDS 可能未在域控制器上运行。 请手动创建/运行 KDS。

要找到 9001 和 9002 EventID，请转到“应用程序和服务日志”>“Microsoft”>“Windows”>“安全 - Netlogon”。

[![“事件 9001”窗口的屏幕截图。不能在本地将帐户用作 M S A，因为计算机不支持所有帐户加密类型。](media/azure-ad-hybrid-sync-unable-create-gmsa-kds-domain-controller/2-event-9001.png)](media/azure-ad-hybrid-sync-unable-create-gmsa-kds-domain-controller/2-event-9001.png#lightbox)

![“事件 9002”窗口的屏幕截图。Netlogon 无法将帐户作为托管服务帐户（M S A）添加到本地计算机。](media/azure-ad-hybrid-sync-unable-create-gmsa-kds-domain-controller/3-event-9002.png)

使用以下命令检索服务器设置以获取[支持的加密类型](/zh-cn/windows/security/threat-protection/security-policy-settings/network-security-configure-encryption-types-allowed-for-kerberos)：

```
C:\windows\system32>reg query "HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Policies\System\Kerberos\Parameters"

HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Policies\System\Kerberos\Parameters
    SupportedEncryptionTypes    REG_DWORD    0x7ffffff8
```

在命令中，DWORD *0x7ffffff8* 代表 *AES128\_HMAC\_SHA1 AES256\_HMAC\_SHA1*。

在 Active Directory 用户和计算机管理单元 (*dsa.msc*) 中， 打开域控制器的 provAgentgMSA 属性:

1. 选择“属性编辑器”选项卡。
2. 选择“msDS-SupportedEncryptionTypes”属性，然后选择“编辑”。

![预配代理 g M S A 属性对话框“属性编辑器”选项卡的屏幕截图。“整数属性编辑器”对话框位于顶部。](media/azure-ad-hybrid-sync-unable-create-gmsa-kds-domain-controller/4-provagentgmsa-properties-integer-attribute-editor.png)

验证服务器提供的加密类型与帐户接受的加密类型之间是否存在不匹配。

要解决此问题，请从 provAgentgMSA 帐户中删除 RC4， 方法是在域控制器中运行以下命令：

```
Set-ADServiceAccount -Identity provAgentgMSA -KerberosEncryptionType AES128,AES256
```

接下来，重启预配代理服务器并重新安装代理。

有关此问题的详细信息，请参阅 [“无法安装服务帐户”。提供的上下文与目标不匹配。](/zh-cn/archive/blogs/joelvickery/cannot-install-service-account-the-provided-context-did-not-match-the-target)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/azure-ad-hybrid-sync-unable-create-gmsa-kds-domain-controller)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
