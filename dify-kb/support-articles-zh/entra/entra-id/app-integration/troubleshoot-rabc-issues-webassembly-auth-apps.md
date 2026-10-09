# 在 Microsoft Entra ID 的 WebAssembly 身份验证中添加角色声明支持

本文提供有关解决开发 WebAssembly 身份验证应用中基于角色的访问控制问题的指南。

## 症状

生成 WebAssembly 身份验证应用并尝试在应用中实现基于角色的访问控制时，会收到以下错误消息：

- 无权访问此资源。
- Microsoft.AspNetCore.Authorization.DefaultAuthorizationService[2]授权失败。 未满足这些要求：RolesAuthorizationRequirement：User.IsInRole 必须满足以下角色之一：（ROLE\_NAME）

## 原因

WebAssembly 身份验证堆栈可能会将角色声明强制转换为单个字符串。 这可以防止适当的基于角色的访问控制。

## 解决方案

你可以实现自定义用户工厂来修改角色声明映射的行为。 为此，请按照下列步骤操作。

#### 步骤 1：创建自定义用户工厂

创建自定义用户工厂（CustomUserFactory.cs）：

```
using Microsoft.AspNetCore.Components.WebAssembly.Authentication;
using Microsoft.AspNetCore.Components.WebAssembly.Authentication.Internal;
using System.Security.Claims;
using System.Text.Json;

public class CustomUserFactory : AccountClaimsPrincipalFactory<RemoteUserAccount>
{
    public CustomUserFactory(IAccessTokenProviderAccessor accessor)
        : base(accessor)
    {
    }

    public async override ValueTask<ClaimsPrincipal> CreateUserAsync(
        RemoteUserAccount account,
        RemoteAuthenticationUserOptions options)
    {
        var user = await base.CreateUserAsync(account, options);
        var claimsIdentity = (ClaimsIdentity?)user.Identity;

        if (account != null && claimsIdentity != null)
        {
            MapArrayClaimsToMultipleSeparateClaims(account, claimsIdentity);
        }

        return user;
    }

    private void MapArrayClaimsToMultipleSeparateClaims(RemoteUserAccount account, ClaimsIdentity claimsIdentity)
    {
        foreach (var prop in account.AdditionalProperties)
        {
            var key = prop.Key;
            var value = prop.Value;
            if (value != null && (value is JsonElement element && element.ValueKind == JsonValueKind.Array))
            {
                // Remove the Roles claim with an array value, and create new claims with the same key
                claimsIdentity.RemoveClaim(claimsIdentity.FindFirst(prop.Key));
                var claims = element.EnumerateArray().Select(x => new Claim(prop.Key, x.ToString()));
                claimsIdentity.AddClaims(claims);
            }
        }
    }
}
```

#### 步骤 2：将角色映射和自定义用户工厂添加到身份验证中间件

如果使用的是 `AddOidcAuthentication`：

```
builder.Services.AddOidcAuthentication(options =>
{
    builder.Configuration.Bind("AzureAd", options.ProviderOptions);
    options.ProviderOptions.AdditionalProviderParameters.Add("domain_hint", "contoso.com");
    options.ProviderOptions.DefaultScopes.Add("User.Read");
    options.UserOptions.RoleClaim = "roles";
    options.ProviderOptions.ResponseType = "code";
}).AddAccountClaimsPrincipalFactory<CustomUserFactory>();
```

如果使用的是 `AddMsalAuthentication`：

```
builder.Services.AddMsalAuthentication(options =>
{
    builder.Configuration.Bind("AzureAd", options.ProviderOptions.Authentication);
    options.ProviderOptions.AdditionalScopesToConsent.Add("user.read");
    options.ProviderOptions.DefaultAccessTokenScopes.Add("api://{your-api-id}");
    options.UserOptions.RoleClaim = "roles";
}).AddAccountClaimsPrincipalFactory<CustomUserFactory>();
```

#### 步骤 3：将 `Authorize` 属性添加到 Blazor 页面

```
@attribute [Authorize(Roles="access_as_user")]
```

接下来，将应用角色添加到应用注册，将用户分配到应用角色，然后将应用配置为使用分配的应用角色。

## 参考

- [使用身份验证库保护 ASP.NET Core Blazor WebAssembly 独立应用](/zh-cn/aspnet/core/blazor/security/webassembly/standalone-with-authentication-library)
- [GitHub 项目：已实现此解决方案的示例](https://github.com/willfiddes/aad-webassembly-auth)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/troubleshoot-rabc-issues-webassembly-auth-apps)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
