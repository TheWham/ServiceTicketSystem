# Microsoft Entra Connect 无法向 Microsoft Entra ID 进行身份验证时出错：无法与 Windows Azure Active Directory 服务通信

## 概要

本文提供有关排查标识同步客户端在出现未经身份验证的代理服务器时无法向 Microsoft Entra ID 进行身份验证的问题的信息。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 3013032

## 现象

如果环境包含未经身份验证的代理服务器，则标识同步客户端可能无法向 Microsoft Entra ID 进行身份验证。

例如，使用标识同步客户端（如 Microsoft Entra Connect、Azure Active Directory 同步服务（Azure AD Sync）或 Azure Active Directory 同步工具时遇到此问题。

如果使用 Microsoft Entra Connect 或 Azure AD Sync：

该向导显示以下配置错误消息：

> 已准备好配置。  
> 我们收集了足够的信息来配置 Azure AD Sync，现在将创建默认配置。  
> 即使在 5 次重试后也失败。 操作：PingProvisioningServiceEndPoint，异常：无法与 Windows Azure Active Directory 服务通信。 跟踪 ID：01601250-7951-469c-8973-34e2a8e1ca10 有关详细信息，请参阅事件日志。

出现此问题时，Microsoft Entra Connect 或 Azure AD Sync 日志中记录了类似于以下内容的“错误 906”条目。 此条目指示标识同步设备尝试直接连接到 Internet。

> AzureActiveDirectoryDirectorySyncTool 错误：906：System.Management.Automation.CmdletInvocationException：即使在 5 次重试后也失败。 操作：PingProvisioningServiceEndPoint，异常：无法与 Windows Azure Active Directory 服务通信。 跟踪 ID：90edf657-f63e-46cc-94ec-df88817f4c73 请参阅事件日志了解更多详细信息。
> >--- Microsoft.IdentityManagement.PowerShell.ObjectModel.SynchronizationConfigurationValidationException：即使在 5 次重试后也失败。 操作：PingProvisioningServiceEndPoint，异常：无法与 Windows Azure Active Directory 服务通信。 跟踪 ID：90edf657-f63e-46cc-94ec-df88817f4c73 请参阅事件日志了解更多详细信息。

如果使用 Azure Active Directory 同步工具：

以下目录同步事件 ID 0 记录在标识同步客户端计算机的应用程序日志中：

> 日志名称：应用程序  
> 源：目录同步  
> 事件 ID：0  
> 任务类别：无  
> 级别： 错误  
> 说明:  
> 无法与身份验证服务建立连接。 联系 Technical Support.0 GetAuthState（） 失败并显示 -2147186688 状态。 HResult：0。 请与技术支持部门联系。 （0x80048862）

此外，网络监视器（Netmon.exe）跟踪指示Microsoft Online Services 登录助手使用代理和访问 `login.microsoftonline.com`。

## 原因

出现此问题的原因是标识同步设备所基于的 Microsoft .NET Framework 无法识别代理设置。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 打开以下文件： `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\Config\machine.config`
2. 将以下文本添加到文件末尾：

   `<system.net> <defaultProxy> <proxy usesystemdefault="true" proxyaddress="http://<PROXYIP>:80" bypassonlocal="true" /> </defaultProxy> </system.net>`

   注意

   在此文本中，占位符 <PROXYIP> 表示实际的代理 IP 地址。 有关此上下文中的代理设置的详细信息，请参阅[元素（网络设置）。](/zh-cn/dotnet/framework/configure-apps/file-schema/network/proxy-element-network-settings)

## 详细信息

有关详细信息，请参阅 [通过 HTTP 代理服务器](https://support.microsoft.com/help/318140)使用 Web 服务的 .NET 客户端上的错误。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/unable-communicate-windows-service)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
