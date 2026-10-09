# Error when you run Azure PowerShell cmdlets: Method invocation failed

This article discusses an issue in which you receive an error message "Method invocation failed because [System.Object[]] doesn't contain a method named 'RemoveAll'." when you run Azure PowerShell cmdlets.

_Original product version:_ &nbsp; Microsoft Entra ID, Cloud Services (Web roles/Worker roles)  
_Original KB number:_ &nbsp; 3072418

## Symptoms

When you run Windows Azure PowerShell cmdlets, you receive an error message that resembles the following message:

> Method invocation failed because [System.Object[]] doesn't contain a method named 'RemoveAll'.

## Cause

This problem occurs for either of the following reasons:

- You are using an outdated version of Azure PowerShell.
- You are using a method name that does not exist.

## Resolution

To resolve this problem, do either of the following:

- Install the latest version of Azure PowerShell. To upgrade the program, see [How to install and configure Azure PowerShell](/powershell/azure).
- Make sure that you are using the correct method name.


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/dir-dmns-obj/method-invocation-failed-error) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
