# Error (LogonUser() Failed with error code: 1789) after you enter enterprise administrator credentials in the Azure Active Directory Sync tool Configuration Wizard

## Summary 

This article provides guidance on resolving the "LogonUser() Failed with error code: 1789" error after you enter enterprise administrator credentials in the Azure Active Directory Sync tool configuration wizard.

_Original product version:_ &nbsp; Cloud Services (Web roles/Worker roles), Microsoft Entra ID, Microsoft Intune, Azure Backup, Office 365 Identity Management  
_Original KB number:_ &nbsp; 2508225

## Symptoms

After you enter your enterprise admin credentials in the Microsoft Azure Active Directory Sync Tool Configuration Wizard, you receive the following error message:

> LogonUser() Failed with error code: 1789

## Cause

This issue typically occurs when the computer on which you're running the Directory Sync tool can't authenticate with Active Directory.

## Resolution

To resolve this issue, use one or more of the following methods:

- Restart the computer.
- Join the computer to a workgroup and then join the computer back to the domain.
  1. Select **Start**, right-click **Computer**, and then select **Properties**.
  2. Under **Computer name, domain, and workgroup settings**, select **Change Settings**.
  3. Select the **Computer Name** tab, and then select **Change**.
  4. Select the **Workgroup** option, and then type a workgroup in the **Workgroup** dialog box.
  5. Restart the computer.
  6. Repeat steps 1 through 3.
  7. Select the **Domain** option, and then type the domain name in the **Domain** dialog box to add the computer back to the domain.
  8. Restart the computer.


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/error-code-1789-configuration-wizard) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
