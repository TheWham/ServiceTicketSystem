# 如何在没有用户选择提示的情况下注销 OpenID Connect/OAuth2 应用程序

## 概要

默认情况下，当你注销在 Microsoft Entra ID 中注册的 OpenID Connect/OAuth2 应用程序时，系统会提示你选择要注销的用户帐户，即使只有一个帐户可用。 本文提供了绕过此行为的分步指南。

## 步骤 1：为login\_hint添加可选声明

1. 至少以[云应用程序管理员](https://entra.microsoft.com/)身份登录到 [Microsoft Entra 管理中心](/zh-cn/entra/identity/role-based-access-control/permissions-reference#cloud-application-administrator)。
2. 访问 **Entra ID**>**应用注册**。
3. 选择要为其配置可选声明的应用程序。
   1. 在“管理”下，选择“令牌配置” 。
   2. 选择 **“添加可选声明**”。
   3. 选择要配置的令牌类型，例如 **ID**。
   4. 选择要添加的可选声明 **login\_hint** 。
   5. 选择 **并添加**。

[![显示login_hint声明的屏幕截图。](media/sign-out-of-openid-connect-oauth2-applications-without-user-selection-prompt/login-hint-optional-claim.png)](media/sign-out-of-openid-connect-oauth2-applications-without-user-selection-prompt/login-hint-optional-claim.png#lightbox)

有关添加可选声明的详细信息，请参阅 [在 ID 令牌、访问令牌和 SAML 令牌中配置和管理可选声明](/zh-cn/entra/identity-platform/optional-claims)。

## 步骤 2：确保在原始登录请求中包含“profile”和“openid”作用域

下面是请求 URL 中包含 `openid` 和 `profile` 的 OpenID 连接范围的两个示例：

- 如果使用授权代码流：

  ```
  https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/v2.0/authorize?
  response_type=code&client_id=<client_id>&scope=openid+user.read+profile&redirect_uri=https://login.microsoftonline.com/common/oauth2/nativeclient
  ```

  在令牌终结点调用期间，获取访问令牌时也会返回一个 `id_token` 。
- 如果使用隐式流（不建议）：

  ```
  https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/v2.0/authorize?
  response_type=id_token&client_id=<client_id>&scope=openid+user.read+profile&redirect_uri=https://login.microsoftonline.com/common/oauth2/nativeclient
  ```

  登录后，当 Microsoft Entra ID 重定向回到您的应用程序时，会返回一个 `id_token`。

在返回的 `id_token` 中，包含了 `login_hint` 声明的值。

## 步骤 3：在注销请求中传递logout\_hint参数

发送注销请求时，请在注销请求中传递 `logout_hint` 参数及其关联的声明值 `login_hint`。

```
https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/v2.0/logout?
post_logout_redirect_uri=https://login.microsoftonline.com/common/oauth2/nativeclient
&logout_hint=<login_hint_claim_value>
```

## 详细信息

对于使用 Microsoft JavaScript 身份验证库（MSAL.js）的应用程序，使用用户帐户发送 `EndSessionRequest` 时，MSAL.js 自动发送 `logout_hint` 参数以及 `login_hint` 声明（如果检测到）。

下面是一个示例代码片段：

```
logout() {
    var account = this.authService.instance.getAllAccounts()[0];
    let logoutRequest:EndSessionRequest = {
      account: account
    };
 
    this.authService.logout(logoutRequest);
  }
```

对于使用 Microsoft Identity Web 或 ASP.NET（Core） OpenID Connect 身份验证的应用程序，可以添加自定义代码以在注销请求中设置 `logout_hint` 参数。

下面是一个示例代码片段：

```
services.Configure<OpenIdConnectOptions>(OpenIdConnectDefaults.AuthenticationScheme, options =>

{

  // Custom code here.
  options.Events.OnRedirectToIdentityProviderForSignOut = (context) =>

  {

    var login_hint = context.HttpContext.User.Claims.Where(c => c.Type == "login_hint").FirstOrDefault();

    if (login_hint != null)

    {

      context.ProtocolMessage.SetParameter("logout_hint", login_hint.Value);

    };

    return Task.FromResult(true);

  };

});
```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/sign-out-of-openid-connect-oauth2-applications-without-user-selection-prompt)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
