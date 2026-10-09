# 运行 Microsoft Entra Connect 向导时出错：无法配置密码写回

## 概要

本文介绍运行 Microsoft Entra Connect 向导以设置密码写回时出现错误消息的问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 3185990

## 现象

运行 Microsoft Entra Connect 向导时，在配置密码写回期间收到以下错误消息：

> 无法配置密码写回。 确保拥有所需的许可证。

## 原因

如果满足以下条件之一，则会出现此问题：

- 用于设置 Microsoft Entra Connect 的管理员帐户没有相应的许可证。
- 安装 Microsoft Entra Connect 的服务器上的时间不同步。
- TLS 设置已正确配置。

## 解决方法

若要重新搁置此问题，请执行以下步骤：

1. [启用 TLS 1.2](/zh-cn/azure/active-directory/hybrid/reference-connect-tls-enforcement)。
2. 确保用于启用密码写回的管理员帐户是云管理员帐户（在 Microsoft Entra ID 中创建），而不是联合帐户（在本地 Active Directory中创建并同步到 Microsoft Entra ID）。 此外，请确保帐户具有相应的Microsoft Entra 订阅许可证。
3. 确保时间不偏斜。 在权威时间服务器上，执行“配置 Windows 时间”服务以使用“如何在 Windows Server 中配置权威时间服务器”的外部时间源[部分**的步骤**](https://support.microsoft.com/help/816042)

确保安装 Microsoft Entra Connect 的服务器上的时间与权威时间服务器上的时间匹配。

## 详细信息

如果遇到的问题是本地环境和Microsoft云服务之间存在很大的时间差异的情况，

可以在 Microsoft Entra Connect 同步日志中看到以下条目。 日志位于 `%appdata%\Local\AADConnect` 文件夹中。

```
Error <Date> <Time> ADSync 6306 Server "The server encountered an unexpected error while performing an operation for the client.

Error <Date> <Time> ADSync 6800 MA Extension "The password management extension encountered an error.
 The stack trace is:
 ""Couldn't connect to any service bus endpoint(s)

Error <Date> <Time> PasswordResetService 32001 None TrackingId: 3f369fe9-c121-4450-8661-82b095bdbf0a,
Couldn't connect to any service bus endpoint(s), Details:

Error <Date> <Time> PasswordResetService 31044 None TrackingId: 3f369fe9-c121-4450-8661-82b095bdbf0a,
Password writeback service is not in a healthy state. No serviceHost for service bus endpoints are in
running state. Please refer aka.ms/ssprtroubleshoot, Details: Version: 5.0.0.686
```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/unable-configure-pwd-writeback-error)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
