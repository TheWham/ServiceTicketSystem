# Error when you run the IdFix tool: IdFix.exe is not a valid Win32 application

_Original product version:_ &nbsp; Cloud Services (Web roles/Worker roles), Microsoft Entra ID, Microsoft Intune, Azure Backup, Office 365 Identity Management  
_Original KB number:_ &nbsp; 2859165

## Symptoms

When you try to run the IdFix DirSync Error Remediation Tool in your on-premises Active Directory Domain Services (AD DS) environment, you receive the following error message:

> IdFix.exe is not a valid Win32 application

## Cause

This issue occurs if you're running the IdFix tool on an operating system that's not supported for the tool.

## Resolution

Install and run the IdFix tool on a computer that's running the 64-bit version of Windows 7 or a later version.

## More information

For more information about the IdFix tool, see [IdFix DirSync Error Remediation Tool](https://github.com/microsoft/idfix) (This includes a list of system requirements.).


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/idfix-not-valid-win32-application) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
