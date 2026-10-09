# Microsoft.Identity.Client.MsalClientException：无法获取用户名

## 概要

本文提供了一个解决方案，用于解决应用程序将集成 Windows 身份验证（IWA）与Microsoft身份验证库（MSAL）一起使用时出现的“无法获取用户名”错误。

## 症状

当应用程序将 IWA 与 MSAL 一起使用时，如果调用 `AcquireTokenByIntegratedWindowsAuth` 方法，如下所示：

```
result = await app.AcquireTokenByIntegratedWindowsAuth(scopes)
```

遇到以下错误之一：

- > Microsoft.Identity.Client.MsalClientException：无法获取用户名 —>  
  > System.ComponentModel.Win32Exception：未在帐户名称和安全 ID 之间进行映射
- > Microsoft.Identity.Client.MsalClientException：无法获取用户名 —>  
  > System.ComponentModel.Win32Exception：访问被拒绝

## 原因

此错误源自 Windows。 发生此情况的原因是 MSAL 从中调用 `secur32.dll` 函数。 有关详细信息，请参阅 [MSAL WindowsNativeMethods.cs - GetUserNameEx](https://github.com/AzureAD/microsoft-authentication-library-for-dotnet/blob/01ecd12464007fc1988b6a127aa0b1b980bca1ed/src/client/Microsoft.Identity.Client/Platforms/Features/DesktopOS/WindowsNativeMethods.cs#L66)。

## 解决方案

注释

在开始之前，请确保满足以下最低要求：

- 将应用程序作为本地 Active Directory 用户运行，而不是本地计算机用户帐户。
- 运行应用程序的设备已加入域。

若要解决此问题，请将用户名传递给 `AcquireTokenByIntegratedWindowsAuth`。

如果用户名事先已知，可以手动将其传递给 MSAL，如下所示：

```
result = await app.AcquireTokenByIntegratedWindowsAuth(scopes).WithUsername("<service-account>@contoso.com")
```

如果事先不知道用户名，请动态检索用户名，然后使用下列方法之一将其传递给该 `AcquireTokenByIntegratedWindowsAuth` 用户名：

- 使用 `System.Security.Principal.WindowsIdentity.GetCurrent()`

  下面是代码示例：

  ```
  string username = System.Security.Principal.WindowsIdentity.GetCurrent().Name;
  result = await app.AcquireTokenByIntegratedWindowsAuth(scopes).WithUsername(username)
  ```

  注释

  如果返回的用户名不包含域，此方法将失败并返回不同的错误。 若要正确与 Microsoft Entra ID 集成，必须以用户主体名称的格式传递用户名。
- 使用 `PublicClientApplication.OperatingSystemAccount.Username`

  下面是代码示例：

  ```
  string username = PublicClientApplication.OperatingSystemAccount.Username;
  result = await app.AcquireTokenByIntegratedWindowsAuth(scopes).WithUsername(username)
  ```

  注释

  此方法尝试访问 Windows 帐户代理以将用户登录到设备。 如果应用程序在 Internet Information Services（IIS）或 Windows Server 上运行，则它不起作用。

## 参考文献

[将 MSAL.NET 与集成 Windows 身份验证 （IWA） 配合使用](/zh-cn/entra/msal/dotnet/acquiring-tokens/desktop-mobile/integrated-windows-authentication)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/msal-client-exception-failed-to-get-user-name)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
