# 使用 Azure B2C 自定义策略在 ASP.NET Core 应用中出现IDX10501错误

## 概要

本指南讨论“IDX10501”错误的原因，并提供一个分步解决方案来解决此错误。

## 现象

在 [与 Azure Active Directory B2C（Azure AD B2C）集成的 ASP.NET Core 应用程序中实现自定义策略](/zh-cn/azure/active-directory-b2c/enable-authentication-web-application-options#pass-the-azure-ad-b2c-policy-id) 时，可能会遇到以下IDX10501错误：

> IDX10501：签名验证失败。 无法匹配键：儿童：“System.String”类型的 PII 已隐藏。 有关详细信息，请参阅 https://aka.ms/IdentityModel/PII.]'。 TokenValidationParameters 中的密钥数：“0”。 配置中的密钥数：“1”。 捕获的异常：“System.Text.StringBuilder”类型的[PII 已隐藏。 有关详细信息，请参阅 https://aka.ms/IdentityModel/PII.]'。 token： '[PII of type 'System.IdentityModel.Tokens.Jwt.JwtSecurityToken' is hidden. 有关详细信息，请参阅 https://aka.ms/IdentityModel/PII.]'。

## 了解错误

当自定义策略重定向到应用时，为什么生成此错误？ 在 ASP.NET Core 中，只要用户经过身份验证和授权，并且重定向页面就存在到包含 ID 令牌的 Web 应用，ASP.NET Core 中间件会尝试验证此 ID 令牌以确保重定向是正版的。 若要验证 ID 令牌，中间件需要用于对 ID 令牌进行签名的签名证书的公钥。 中间件通过查询 Azure Active Directory B2C 来获取此公钥。 具体而言，中间件使用 Azure Active Directory B2C 中的“元数据”终结点，该终结点提供身份验证信息，包括用于签名证书的任何公钥。

创建自定义策略时，需要创建或上传签名证书。 此签名证书不同于用于 Azure Active Directory B2C 中的内置用户流的证书。 这意味着可从 Azure Active Directory B2C 的“元数据”终结点访问的公钥不包含自定义策略的公钥。 自定义策略实际上有自己的元数据终结点。

中间件使用的终结点由 Microsoft.Identity.Web 配置，并在应用启动时设置。 由于已设置元数据 URL，因此在运行时调用自定义策略会创建中间件在验证返回令牌时查看错误的元数据 URL 的方案。

## 解决方案

若要解决此问题，必须为其他自定义策略配置正确的元数据终结点。 为此，请创建第二个身份验证方案来处理自定义策略。 通过使用此附加身份验证方案，可以在启动时设置正确的元数据终结点。 此过程使用以下步骤：

1. 向应用注册添加其他重定向 URI。
2. 在应用中配置其他 B2C 身份验证方案。
3. 将操作添加到所需的控制器。
4. 在布局中实现创建的操作。

代码示例： [使用自定义 B2C 策略](https://github.com/mbukovich/ExtraB2CPolicyMVC) ASP.NET 核心 Web 应用。

### 先决条件

在继续此过程之前，请确保具备：

- Azure B2C 目录
- B2C 身份验证的应用注册
- [设置的标准用户流](/zh-cn/azure/active-directory-b2c/tutorial-create-user-flows?pivots=b2c-user-flow)
- [添加到目录的自定义 B2C 策略](/zh-cn/azure/active-directory-b2c/tutorial-create-user-flows?pivots=b2c-custom-policy)
- 通过Microsoft.Identity.Web 进行 B2C 身份验证配置的现有 ASP.NET Core Web 应用

  有关详细信息，请参阅 [使用 Azure AD B2C 在自己的 Web 应用中启用身份验证](/zh-cn/azure/active-directory-b2c/enable-authentication-web-application?tabs=visual-studio)

### 步骤 1：添加其他重定向 URI

在应用注册中，必须为自定义策略添加另一个重定向 URI。 在这种情况下，无法使用现有的重定向 URI，因为它可能会导致 Web 应用混淆。 你将设置两个不同的身份验证方案。 但是，当 B2C 策略重定向到 Web 应用时，中间件将不知道要使用的身份验证方案。 因此，需要单独的重定向 URI 来清楚地区分重定向与现有和新身份验证方案之间的重定向。

执行以下步骤：

1. 导航到Azure 门户[中的应用](https://portal.azure.com)注册。
2. 在 **“管理** ”部分中，选择“ **身份验证**”。
3. 在 **“重定向 URI** ”部分中，选择“ **添加 URI**”。
4. 添加重定向 URI。 在这种情况下，新的重定向 URI 为 `https://localhost:44321/signin-oidc-editemail`。

[![添加重定向 URI 的屏幕截图。](media/troubleshoot-error-idx10501-aspnet-b2c/add-redirect-uri.png)](media/troubleshoot-error-idx10501-aspnet-b2c/add-redirect-uri.png#lightbox)

备注

每个自定义策略都需要自己的重定向 URI。 例如，如果要添加两个自定义策略，则必须创建两个身份验证方案和两个重定向 URI。

### 步骤 2：配置其他身份验证方案

此过程涉及向控制器添加操作，以向用户发出质询。 在创建此操作之前，请使用其他身份验证方案配置应用。 这需要更新Appsettings.json文件和Startup.cs文件。

#### 更新 `Appsettings.json`

为自定义策略添加以下配置：

```
"<name-of-your-configuration>": {
    "Instance": "https://<B2C-tenant-name>.b2clogin.com",
    "ClientId": "<client-id-of-your-app-registration>",
    "CallbackPath": "/<endpoint-of-your-new-redirect-uri>",
    "SignedOutCallbackPath": "/signout/<built-in-sign-in-sign-up-policy>",
    "Domain": "<B2C-tenant-name>.onmicrosoft.com",
    "SignUpSignInPolicyId": "<built-in-sign-in-sign-up-policy>"
},
```

`Appsettings.json` 的示例

```
{
  "AzureADB2C": {
    "Instance": "https://markstestorganization1.b2clogin.com",
    "ClientId": "00001111-aaaa-2222-bbbb-3333cccc4444",
    "CallbackPath": "/signin-oidc",
    "SignedOutCallbackPath": "/signout/B2C_1_signupsignin1",
    "Domain": "markstestorganization1.onmicrosoft.com",
    "SignUpSignInPolicyId": "B2C_1_signupsignin1",
    "ResetPasswordPolicyId": "B2C_1_PasswordReset1",
    "EditProfilePolicyId": "B2C_1_editProfileTest1"
  },
  "AzureADB2CEditEmail": {
    "Instance": "https://markstestorganization1.b2clogin.com",
    "ClientId": "00001111-aaaa-2222-bbbb-3333cccc4444",
    "CallbackPath": "/signin-oidc-editemail",
    "SignedOutCallbackPath": "/signout/B2C_1_signupsignin1",
    "Domain": "markstestorganization1.onmicrosoft.com",
    "SignUpSignInPolicyId": "B2C_1_signupsignin1"
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft": "Warning",
      "Microsoft.Hosting.Lifetime": "Information"
    }
  },
  "AllowedHosts": "*"
}
```

**重要注意事项**

- 可以为第二个 B2C 配置选择任何名称。 此配置将用于单个自定义策略。 如果必须添加更多自定义策略，则必须在AppSettings.json文件中包括其他 B2C 配置。 出于此原因，我们建议为 JSON 对象指定一个反映关联自定义策略的名称。
- CallbackPath 值是遵循域的重定向 URI 的一部分。 例如，如果重定向 URI 为 `https://localhost:44321/signin-oidc-editemail`，则 CallbackPath 将为 `/signin-oidc-editemail`。
- 必须在身份验证方案中包括标准的内置注册/登录用户流，以确保如果用户尝试访问自定义策略而不登录，则系统会提示用户登录。

#### 更新 `Startup.cs`

在Startup.cs文件中配置其他身份验证方案。 在 `ConfigureServices` 函数中，添加以下代码：

```
// Create another authentication scheme to handle extra custom policy
services.AddAuthentication()
       .AddMicrosoftIdentityWebApp(Configuration.GetSection("<name-of-json-configuration>"), "<Arbitrary-name-for-Auth-Scheme>", "<Arbitrary-name-of-Cookie-Scheme>");

services.Configure<OpenIdConnectOptions>("<Arbitrary-name-for-Auth-Scheme>", options =>
    {
        options.MetadataAddress = "<Metadata-Address-for-Custom-Policy>";
    });
```

- 必须同时为身份验证方案和关联的 Cookie 方案设置自定义名称。 Microsoft.Identity.Web 将使用指定的名称创建这些方案。
- 替换为 `<name-of-json-configuration>` 上一步中的 JSON 配置的名称。 根据本文中的示例，应该如此 `AzureADB2CEditEmail`。
- 替换为 `<Your-Custom-Metadata-URL>` 在 Azure AD B2C 中的自定义策略下找到的 OpenID Connect 发现终结点 URL。

#### 如何获取自定义策略的元数据地址

获取元数据地址非常重要，因为中间件会使用此地址来获取所需的信息来验证自定义策略返回的 ID 令牌。

若要查找元数据地址，请执行以下步骤：

1. 登录到 Azure B2C 门户。
2. 在 **“策略** ”部分中，选择“ **标识体验框架**”。

   ![“标识体验框架”按钮的屏幕截图。](media/troubleshoot-error-idx10501-aspnet-b2c/find-identity-exp-fr.png)
3. 选择“自定义策略**”**，然后选择正在使用的自定义策略。 在本例中，它 **B2C\_1A\_DEMO\_CHANGESIGNINNAME**。

   ![检查自定义策略的屏幕截图。](media/troubleshoot-error-idx10501-aspnet-b2c/custom-policy.png)
4. 元数据地址是在 OpenId Connect 发现终结点**下**列出的 URL。 复制此 URL，并将其粘贴为变量的值 `options.MetadataAddress` 。

### 步骤 3：向控制器添加操作

在控制器中，实现一个操作来触发用户的自定义 B2C 策略质询。 在代码示例中，为简单起见，操作将添加到主控制器。 将以下代码添加到控制器，并调整值和操作名称以满足你的方案。 可以在代码示例中的文件夹中的第 40 `HomeController.cs` 行中找到 `Controllers` 此代码片段：

```
[Authorize]
public IActionResult EditEmail()
{
    var redirectUrl = Url.Content("~/");
    var properties = new AuthenticationProperties { RedirectUri = redirectUrl };
    properties.Items["policy"] = "B2C_1A_DEMO_CHANGESIGNINNAME";
    return Challenge(properties, "B2CEditEmail");
}
```

请确保与 `<Your-Custom-Policy>` 特定策略名称匹配，并与 `<CustomAuthScheme>` 之前配置的内容一致。

### 步骤 4：在布局中实现操作

在布局中实现操作，以便用户能够实际调用自定义策略。 在代码示例中，以下代码片段根据 [教程](/zh-cn/azure/active-directory-b2c/enable-authentication-web-application)将按钮与现有 B2C 按钮一起添加。 代码片段将添加到文件夹中文件`_LayoutPartial.cshtml`的第 13 `Views/Shared` 行。 请注意，该 `asp-controller` 属性设置为 `Home` 引用主控制器，该 `asp-action property` 属性设置为 `EditEmail` 引用在主控制器中创建的操作。 有关详细信息，请参阅 [“添加 UI 元素](/zh-cn/azure/active-directory-b2c/enable-authentication-web-application?tabs=visual-studio#step-4-add-the-ui-elements)”。

```
<li class="navbar-btn">
    <form method="get" asp-area="" asp-controller="Home" asp-action="EditEmail">
        <button type="submit" class="btn btn-primary">Edit Email</button>
    </form>
</li>
```

如果你有一个不使用部分布局的现有应用，并且只需要一个快速链接来测试自定义策略，则可以使用以下标记创建基本链接。 如果未将操作添加到主控制器，请确保替换指示的值并引用正确的控制器。

```
<a asp-area="" asp-controller="Home" asp-action="replace-with-your-controller-action">Replace with text that describes the action</a>
```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/troubleshoot-error-idx10501-aspnet-b2c)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
