# Error when trying to reset password in Azure, Office 365, or Intune: We could not verify your account

_Original product version:_ &nbsp; Cloud Services (Web roles/Worker roles), Microsoft Entra ID, Microsoft Intune, Azure Backup, Office 365 Identity Management  
_Original KB number:_ &nbsp; 2951274

## Symptoms

When a new user tries to reset password in Microsoft Azure, Microsoft Office 365, or Microsoft Intune, the user receives the following error message:

> Reset your password
>
> We could not verify your account
>
> If you'd like, we can contact an administrator in your organization to reset your password for you..

## Resolution

Assign a Microsoft Entra ID P1 or P2 license to the user. Users must have a Microsoft Entra ID P1 or P2 license to be able to reset their own password.


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/cannot-verify-account-reset-pwd) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
