# 运行 Azure PowerShell cmdlet 时出错：方法调用失败

本文讨论了在运行 Azure PowerShell cmdlet 时收到错误消息“方法调用失败的问题，因为 [System.Object[]] 不包含名为”RemoveAll“的方法。

*原始产品版本：*Microsoft Entra ID、云服务（Web 角色/辅助角色）  
*原始 KB 数：* 3072418

## 现象

运行 Windows Azure PowerShell cmdlet 时，会收到类似于以下消息的错误消息：

> 方法调用失败，因为 [System.Object[]] 不包含名为“RemoveAll”的方法。

## 原因

出现此问题的原因之一：

- 你使用的是过时的 Azure PowerShell 版本。
- 你使用的是不存在的方法名称。

## 解决方法

若要解决此问题，请执行下列操作之一：

- 安装最新版本的 Azure PowerShell。 若要升级程序，请参阅 [如何安装和配置 Azure PowerShell](/zh-cn/powershell/azure)。
- 请确保使用正确的方法名称。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/dir-dmns-obj/method-invocation-failed-error)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
