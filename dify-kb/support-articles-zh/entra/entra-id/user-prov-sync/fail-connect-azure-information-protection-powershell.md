# 无法使用 Windows PowerShell 连接到 Azure 信息保护

注意

Microsoft Azure 信息保护以前称为 azure Rights Management Microsoft。

## 概要

本文解决了无法在 Office 365 中使用 Windows PowerShell 连接到 Azure 信息保护 服务的问题。

*原始产品版本：*Microsoft Entra ID、Azure 信息保护  
*原始 KB 数：* 2797755

## 现象

尝试在 Microsoft 办公室 365 中使用 Windows PowerShell 连接到 Microsoft Azure 信息保护时，会收到如下所示的错误消息：

> `PS C:\> Connect-AipService`
>
> `Connect-AipService : The attempt to connect to the Azure Information Protection service failed. Verify that the user name and password you are using are correct and try again. If you have continued problems, see http://go.microsoft.com/fwlink/?LinkId=251909.`
>
> `The correlation ID is aaaa0000-bb11-2222-33cc-444444dddddd. Please note and provide this value if asked by support for it.`
>
> `At line:1 char:1`
>
> `+ Connect-AipService`
>
> `+ ~~~~~~~~~~~~~~~~~~`
>
> `+ CategoryInfo : NotSpecified: (:) [Connect-AipService], ApplicationFailedException`
>
> `+ FullyQualifiedErrorId : NotSpecified,Microsoft.RightsManagementServices.Online.Admin.PowerShell.ConnectAipServiceCommand`

还可以看到以下错误消息：

> 对象引用未设置为对象实例。

## 原因

如果满足以下一个或多个条件，则会出现此问题：

- 输入了错误的用户名或密码。
- 你不是公司管理员。
- 没有包含 Azure 信息保护的订阅。
- 网络阻止你连接到 Azure 信息保护。
- 你使用的是 Windows PowerShell 7。 使用 PowerShell 7 将导致“对象引用未设置为对象的实例”错误。 有关详细信息，请参阅[已知问题 - Azure 信息保护](/zh-cn/azure/information-protection/known-issues#powershell-support-for-the-azure-information-protection-client)。

## 解决方案

注意

如果未为公司启用 Azure 信息保护，请使用Microsoft 365 管理中心来启用它。 有关如何执行此操作的详细信息，请阅读 [Azure 信息保护部署路线图](/zh-cn/azure/information-protection/deployment-roadmap)。

若要解决此问题，请确保满足以下条件：

- 请确保输入正确的用户名和密码。 若要检查是否正确输入了它们，请登录到 [Office 365 门户](https://portal.office.com)。
- 必须是全局管理员才能连接到 Azure 信息保护。
- 若要使用 Azure 信息保护，必须具有包含 Azure 信息保护的订阅。
- 请与网络管理员协作，确保网络满足[连接到 Azure 信息保护](/zh-cn/azure/information-protection/requirements#firewalls-and-network-infrastructure)的要求。 要求如下：
  - 启用传入 `*.aadrm.com` 和传出连接。
  - 已启用与 `*.cloudapp.net` （`rmsoprod*-b-rms*.cloudapp.net`） 的传入和传出连接。
  - 端口 443 已打开。
- 使用 Windows PowerShell 5。 可以使用命令检查 PowerShell 版本 `$PSVersionTable.PSVersion` 。

## 详细信息

有关 Azure 信息保护的详细信息，请访问 [AIPService](/zh-cn/powershell/module/aipservice/)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/fail-connect-azure-information-protection-powershell)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
