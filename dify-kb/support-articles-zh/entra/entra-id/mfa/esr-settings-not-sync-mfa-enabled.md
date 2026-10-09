# ESR 设置不会与启用多重身份验证同步

*原始产品版本：* Windows 10 版本 1709 所有版本、Windows 10 版本 1703 所有版本、Windows 10 版本 1511 所有版本、Windows 10 版本 1607 所有版本  
*原始 KB 数：* 3193683

## 现象

已在 Microsoft Entra 管理中心和某些 Windows 10 客户端上启用了企业状态漫游（ESR）。 同步的任何支持设置（例如桌面后台或任务栏位置）不会在同一用户的设备之间同步。 以下事件 1098 和 1097 记录在 Microsoft-Windows-AAD/Operational 事件日志中：

```
Log Name:      Microsoft-Windows-AAD/Operational
Source:        Microsoft-Windows-AAD
Event ID:      1098
Task Category: AadTokenBrokerPlugin Operation
Level:         Error
Keywords:      Error,
Error Computer:      Win10client.contoso.com
Description: Error: 0xCAA2000C The request requires user interaction. Code: interaction_required Description: AADSTS50076: The user is required to use multi-factor authentication to access this resource. Please retry with a new authorize request for the resource 'https://syncservice.windows.net/*'. Trace ID: <Trace ID GUID> Correlation ID: <Correlation ID GUID> Timestamp: yyyy-mmmm-dddd 01:30:38Z
TokenEndpoint: https://login.microsoftonline.com/common/oauth2/token Authority: https://login.microsoftonline.com/common
Client ID: <Client ID GUID>
Redirect URI: ms-appx-web://Microsoft.AAD.BrokerPlugin/<Client ID GUID>
Resource: https://syncservice.windows.net/*
Correlation ID (request): <Correlation ID GUID>
Log Name:      Microsoft-Windows-AAD/Operational
Source:        Microsoft-Windows-AAD
Event ID:      1097 Task Category: AadTokenBrokerPlugin
Operation Level:         Warning
Keywords:      Operational,
Operational Computer:      Win10client.contoso.com
Description: Error: 0xCAA90004 Getting token by refresh token failed.
Authority: https://login.microsoftonline.com/common
Client ID: <Client ID GUID> Redirect URI: ms-appx-web://Microsoft.AAD.BrokerPlugin/<Client ID GUID>
Resource: https://syncservice.windows.net/*
Correlation ID (request): <Correlation ID GUID>
```

## 原因

已启用多重身份验证（MFA），这就是为什么企业状态漫游不会提示用户进行其他授权。

## 解决方法

如果设备配置为要求在 Microsoft Entra 管理中心进行多重身份验证，则在使用密码登录到 Windows 10 设备时，可能无法同步设置。 这种类型的多重身份验证配置旨在保护 Azure 管理员帐户。 管理员用户仍可以使用其 Microsoft Passport for Work PIN 登录其 Windows 10 设备，或者在访问其他 Azure 服务（如 Microsoft 办公室 365）时完成多重身份验证，从而同步。

如果 Microsoft Entra 管理员配置Active Directory 联合身份验证服务多重身份验证条件访问策略，并且设备上的访问令牌过期，同步可能会失败。 确保使用 Microsoft Passport for Work PIN 登录和注销，或者在访问 Office 365 等其他 Azure 服务时完成多重身份验证。

## 更多信息

Microsoft正在调查如何改进设备上启用了企业状态漫游和 MFA 授权的体验。

有关详细信息，请参阅 [“设置和数据漫游常见问题解答](/zh-cn/azure/active-directory/devices/enterprise-state-roaming-faqs)”。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/esr-settings-not-sync-mfa-enabled)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
