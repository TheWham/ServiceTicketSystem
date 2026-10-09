# 使用 MSAL SDK 排查 iOS 中的登录提示问题

## 概要

本文提供有关使用Microsoft身份验证库（MSAL）的 iOS 应用中重复登录提示进行故障排除的指导。

## 症状

遵循 [本教程](/zh-cn/azure/active-directory/develop/tutorial-v2-ios)，使用 Microsoft 身份验证库（MSAL）SDK 在 iOS 应用中集成 Microsoft 标识平台的身份验证。 但是，在初始登录后，系统会意外地提示用户多次登录。

## 原因

此问题通常是由 MSAL 使用的 Web 浏览器不允许 Cookie 共享引起的。

本教程使用 MSAL 实现身份验证。 MSAL SDK 通过自动续订令牌来促进身份验证。 它还在设备上的其他应用之间启用单一登录（SSO），并管理用户帐户。

若要使 SSO 正常工作，必须在应用之间共享令牌。 若要满足此要求，必须使用令牌缓存或中转站应用程序，例如适用于 iOS 的 Microsoft Authenticator。 MSAL 中的交互式身份验证需要 Web 浏览器。 在 iOS 上，MSAL 默认使用 Safari 系统浏览器进行交互式身份验证。 此默认设置支持应用之间的 SSO 状态共享。

但是，如果自定义用于身份验证的浏览器配置，例如使用以下选项之一，则默认情况下可能无法启用 Cookie 共享。

| **仅适用于 iOS** | **对于 iOS 和 macOS** |
| --- | --- |
| [SFAuthenticationSession](https://developer.apple.com/documentation/safariservices/sfauthenticationsession?language=objc)   [SFSafariViewController](https://developer.apple.com/documentation/safariservices/sfsafariviewcontroller?language=objc) | [ASWebAuthenticationSession](https://developer.apple.com/documentation/authenticationservices/aswebauthenticationsession?language=objc)   [WKWebView](https://developer.apple.com/documentation/webkit/wkwebview?language=objc) |

## 决议

若要防止重复登录提示，必须在自定义浏览器时允许 Cookie 共享。 若要在 MSAL 和 iOS 应用之间启用 SSO 和 Cookie 共享，请使用以下解决方案之一：

使用 `ASWebAuthenticationSession` 和 Safari 内置浏览器 (`UIApplication.shared.open`)

- 用例：应用将 MSAL 与默认 `ASWebAuthenticationSession` 实例一起使用，并在 Safari 系统浏览器中打开外部链接或注销流。
- **注意：**`ASWebAuthenticationSession` 是 iOS 12+ 上的 MSAL 交互式身份验证的建议方法。 它是 iOS 13+ 上唯一受支持的方法。 此方法保护隐私并与系统浏览器共享 Cookie。 SSO 在 MSAL 和 Safari 浏览器应用程序之间工作，因为它们通过系统身份验证会话共享 Cookie。

使用 `WKWebView`

- 用例：显式配置 MSAL 以供使用 `WKWebView`，应用也用于 `WKWebView` 相关工作流。
- **注意：** 使用 `WKWebView`，以在应用中获得一致的体验。 但是，因为它已沙盒化， `WKWebView` 因此不会与 Safari 系统浏览器或其他应用共享会话 Cookie。 在这种情况下，SSO 支持仅限于在应用中使用。

有关详细信息，请参阅 [自定义 Web 视图和浏览器](/zh-cn/azure/active-directory/develop/customize-webviews)。

**第三方信息免责声明**

本文讨论的第三方产品由独立于微软的公司制造。 Microsoft对这些产品的性能或可靠性不作任何明示或暗示的保证。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/repeat-login-prompts-in-msal-ios-app)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
