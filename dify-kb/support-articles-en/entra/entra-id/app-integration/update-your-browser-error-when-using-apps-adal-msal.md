# "Your browser is not supported or up-to-date" error in MSAL app

## Summary

This article discusses how to resolve the "Your browser is not supported or up-to-date" error that occurs in a Microsoft Authentication Library (MSAL)-based app.

## Symptoms

When you open an app that integrates with MSAL, and you try to register Microsoft Entra ID Multifactor Authentication (MFA), you receive the following error message:

>Your browser is not supported or up-to-date. Try updating it, or else download and install the latest version of Microsoft Edge.
You could also try to access https://aka.ms/mysecurityinfo from another device.

## Cause

This issue occurs if the MSAL app uses outdated web browser controls, such as WebView1. These older controls don't support Microsoft Entra ID MFA registration or the self-service password reset wizard.

## Resolution

### For users

To work around this issue, register for Microsoft Entra ID Multifactor Authentication (MFA) by using a supported browser before you use the app:

1. Open [My Apps](https://myapps.microsoft.com) in Microsoft Edge or another supported browser.
2. Complete the MFA registration process.
3. After successful registration, open the app.

## For developers

To resolve this issue, enable broker authentication by using [Web Account Manager](/entra/identity-platform/scenario-desktop-acquire-token-wam) in the app.

The following sample code creates a client to use Broker Authentication:

```csharp
var pca = PublicClientApplicationBuilder.Create("client_id").WithBroker(new BrokerOptions(BrokerOptions.OperatingSystems.Windows))
```

If Web Account Manager is unavailable (such as on Windows Server 2012), consider using the [default system browser for authentication](/entra/msal/dotnet/acquiring-tokens/using-web-browsers#how-to-use-the-default-system-browser).


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/update-your-browser-error-when-using-apps-adal-msal) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
