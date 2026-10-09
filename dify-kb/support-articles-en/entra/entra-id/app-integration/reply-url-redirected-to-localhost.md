# Microsoft Entra ID is sending the token to an incorrect reply URL endpoint or localhost

## Summary

This article describes a problem in which Microsoft Entra ID is sending the token to an incorrect reply URL endpoint or localhost.

## Symptoms

During single sign-on, if the sign-in request doesn't contain an explicit reply URL (Assertion Consumer Service URL) then Microsoft Entra ID selects any of the configured reply URLs for that application. Even if the application has an explicit reply URL configured, the user might be to redirected `https://127.0.0.1:444`.

When the application was added as a non-gallery app, Microsoft Entra ID created this reply URL as a default value. This behavior has changed and Microsoft Entra no longer adds this URL by default.

## Cause

The user hasn't been granted access to the application in Microsoft Entra ID.

## Resolution

Delete the unused reply URLs configured for the application.

On the SAML-based single sign-on (SSO) configuration page, in the **Reply URL (Assertion Consumer Service URL)** section, delete unused, or default Reply URLs created by the system. For example, `https://127.0.0.1:444/applications/default.aspx`.


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/reply-url-redirected-to-localhost) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
