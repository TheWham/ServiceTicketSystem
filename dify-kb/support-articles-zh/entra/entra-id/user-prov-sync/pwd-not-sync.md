# 更改或重置密码后，密码不会从 Microsoft Entra ID 同步到本地

## 概要

本文介绍在更改或重置密码后，密码不会从 Microsoft Entra ID 同步到本地目录的问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 3187256

## 现象

执行密码重置或密码更改操作时，密码不会使用 Microsoft Entra Connect 从 Microsoft Entra ID 同步到本地目录。

此外，你可能会看到以下消息，否则密码不会写回本地目录：

> 无法处理请求  
> 很抱歉，目前无法重置密码。 这是因为存在临时连接问题，因此，如果稍后重试，重置密码可能会成功。 如果问题仍然存在，请联系管理员重置密码。

## 原因

此问题可能由于多种原因而发生。 下面是已知原因的列表：

- 密码写回不满足先决条件。
- 未正确设置密码写回的权限。
- Microsoft Entra Connect 中的密码重置代理未运行。
- Microsoft Entra ID 中的密码重置服务与运行 Microsoft Entra Connect 的本地环境之间存在网络连接问题。

## 解决方法

在解决此问题之前，请务必了解哪些方案允许密码写回。 下表列出了密码写回发生且不会发生的方案。

| 场景 | 密码写回 |
| --- | --- |
| 执行自助密码重置的用户 `https://passwordreset.microsoftonline.com` | 是 |
| 执行自助密码重置的管理员 `https://passwordreset.microsoftonline.com` | 是 |
| 我的应用或 Office 365 门户中的密码更改 | 是 |
| 使用 Azure 管理门户执行密码重置的管理员 | 是 |
| 使用 Microsoft 365 管理中心 执行密码重置的管理员 | 否 |
| 通过 Azure 管理门户、Microsoft 365 管理中心或 [Microsoft Graph PowerShell](/zh-cn/powershell/microsoftgraph/overview) 模块创建新用户时的密码 | 否 |
| 使用 PowerShell 模块 V1（MSOnline）或 V2（AzureAD）执行密码重置的管理员 | 否 |

若要解决此问题，请参阅[“如何排查密码管理**问题”的**“密码写回](/zh-cn/azure/active-directory/authentication/active-directory-passwords-troubleshoot#troubleshoot-password-writeback)”部分。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/pwd-not-sync)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
