# 错误AADSTS530004 - 未为此组织配置 AcceptCompliantDevice 设置

## 概要

本文讨论当来宾用户访问资源租户中的应用程序或资源并提供解决方案时发生AADSTS530004错误的情况。

## 现象

当来宾用户尝试访问资源租户中的应用程序或资源时，登录过程将失败，并显示以下错误消息：

> AADSTS530004：未为此组织配置 AcceptCompliantDevice 设置。 管理员需要配置此设置，以允许外部用户访问受保护的资源。

此外，当管理员查看主租户中的登录日志时，会显示相同的错误代码。

## 方案 1：符合标准的设备的条件访问策略

将资源租户中的条件访问策略设置为 **“要求设备”标记为合规** 控制，并将策略应用于来宾用户时，可能会出现AADSTS530004错误。

若要解决该错误，请执行以下步骤：

1. 使用用户主租户中的“信任合规设备[”设置创建跨租户访问策略（XTAP）策略](/zh-cn/entra/external-id/cross-tenant-access-settings-b2b-collaboration#to-change-inbound-trust-settings-for-mfa-and-device-claims)。
2. 确保对来宾用户的设备进行身份验证。

   在某些情况下，设备身份验证可能会失败。 有关详细信息，请参阅 [设备身份验证失败](#device-authentication-fails)。
3. 确保来宾用户的设备已加入 Microsoft Intune 或主租户中支持的移动设备管理（MDM）解决方案，并且符合要求。

   注意

   支持多个第三方设备符合性合作伙伴与 Microsoft Intune 集成。 有关详细信息，请参阅 [Intune](/zh-cn/mem/intune/protect/device-compliance-partners) 中的支持第三方设备符合性合作伙伴。 有关配置 Intune 设备符合性的详细信息，请参阅 [监视 Intune 设备符合性策略](/zh-cn/mem/intune/protect/compliance-policy-monitor)的结果。

## 方案 2：已加入混合设备的条件访问策略

当资源租户中的条件访问策略设置为 **“需要”Microsoft Entra 混合加入设备** 控制，并将该策略应用于来宾用户时，可能会出现此错误。

若要解决该错误，请执行以下步骤：

1. 使用用户主租户中的 [Trust Microsoft Entra 混合加入设备](/zh-cn/entra/external-id/cross-tenant-access-settings-b2b-collaboration#to-change-inbound-trust-settings-for-mfa-and-device-claims) 设置创建 XTAP 策略。
2. 确保对来宾用户的设备进行身份验证。

   在某些情况下，设备身份验证可能会失败。 有关详细信息，请参阅 [设备身份验证失败](#device-authentication-fails)。
3. 确保来宾用户的设备 [Microsoft已加入主租户中的 Entra 混合联接](/zh-cn/entra/identity/devices/how-to-hybrid-join) 。

## 方案 3：已批准的客户端应用的条件访问策略

当资源租户中的条件访问策略配置为“ **需要批准的客户端应用** ”控件，并将该策略应用于来宾用户时，可能会出现此错误。

此方案不受支持。 若要解决此错误，请不要将此控件应用于来宾用户。

## 设备身份验证失败

设备身份验证可能在以下条件之一下失败：

- 在 InPrivate 或 Incognito 模式下使用浏览器进行访问时。
- 使用不受支持的浏览器或设备时，尤其是在移动设备上。
- 禁用浏览器 Cookie 时。
- 当桌面或本机应用程序不支持设备身份验证或不使用Microsoft身份验证代理时。

  有关不同设备平台上Microsoft身份验证代理的详细信息，请参阅以下页面：

  - [Windows操作系统](/zh-cn/entra/identity/devices/concept-primary-refresh-token)
  - [安卓](/zh-cn/entra/identity-platform/msal-android-single-sign-on#sso-through-brokered-authentication)
  - [iOS](/zh-cn/entra/msal/objc/single-sign-on-macos-ios#sso-through-authentication-broker-on-ios)
  - [macOS、iOS 和 iPadOS](/zh-cn/entra/identity-platform/apple-sso-plugin)

有关支持的设备平台的详细信息，请参阅 [Microsoft Entra 条件访问 - 设备平台](/zh-cn/entra/identity/conditional-access/concept-conditional-access-conditions#device-platforms)。

若要验证设备声明是否已发送，请查看资源租户中失败或成功的用户的登录日志：

1. 导航到用户的登录日志，找到相关的失败或成功事件。
2. 在 **“设备信息** ”部分下，选中“ **加入类型** ”字段。 此字段指示已传递的设备声明。

## AADSTS 错误代码参考

有关身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/entra/identity-platform/reference-error-codes)。 若要调查单个错误，请 `https://login.microsoftonline.com/error`搜索 。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-aadsts530004-acceptcompliantdevice-setting-not-configured)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
