# Can't modify user mail or phone number information

This article provides a solution to an issue where you can't modify certain personal information for another user, such as mail and phone number.

## Symptoms

You can't modify the following user attributes for another user:

- `mobilePhone`
- `businessPhones`/`telephoneNumber`
- `otherMails`

Most users experiencing this issue are service principals (Microsoft Graph scenario) or Microsoft Entra users that use the client credentials grant type. Additionally, they get a 403 error.

## Cause

This issue occurs due to insufficient permissions. For Microsoft Entra users, the `User.ReadWrite.All` permission can change a user profile except the three user attributes. For service principals (Microsoft Graph scenario), having the `Directory.ReadWrite.All` permission isn't sufficient to modify the three user attributes.

## Solution

To resolve this issue, assign a Helpdesk Administrator, User Administrator, or Global Administrator role to the service principal or user that changes the three attributes, depending on the user that tries to modify the role. Only the three admin roles can make changes to the three attributes.
> **Caution**
> When you assign one of the three admin roles to the service principal or user, you give them the ability to perform tasks at that level.


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/cannot-modify-user-mail-phone-attributes) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
