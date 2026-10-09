# Error when you run the IdFix tool: Current security context is not associated with an Active Directory domain or forest

_Original product version:_ &nbsp; Cloud Services (Web roles/Worker roles), Microsoft Entra ID, Microsoft Intune, Azure Backup, Office 365 Identity Management  
_Original KB number:_ &nbsp; 2859144

## Symptoms

When you run the IdFix DirSync Error Remediation Tool to perform a query in your on-premises Active Directory Domain Services (AD DS) environment, you receive the following error message:

> Exception: Current security context is not associated with an Active Directory domain or forest.

This issue occurs after you log on to the computer by using a user account that's not a member of the domain in which you're running the query. The IdFix tool uses the security context of the user who runs the tool to determine the domain to query.

## Resolution

Log on to the computer by using a user account that's a member of the domain in which you're running the query.

## More information

For more information about the IdFix tool, see [IdFix DirSync Error Remediation Tool](https://github.com/microsoft/idfix).


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/security-context-not-associate-domian) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
