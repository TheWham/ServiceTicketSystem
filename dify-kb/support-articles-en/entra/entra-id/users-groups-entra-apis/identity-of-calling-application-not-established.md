# Error "The identity of the calling application could not be established"

This article provides solutions to the error message "The identity of the calling application could not be established" when using Microsoft Graph.

## Symptoms

When using Microsoft Graph or some services that rely on it, you encounter the following error message:

> The identity of the calling application could not be established

## Cause

This error occurs because the `oid` and `sub` claims are missing from the access token. The root cause is that the service principal doesn't exist in the tenant or the tenant isn't aware of the application.

## Solution

To resolve this error, add the service principal to the tenant and consent to the permissions required by the application.

You can [build an admin consent URL](/entra/identity/enterprise-apps/grant-admin-consent#construct-the-url-for-granting-tenant-wide-admin-consent) like the following one:

`https://login.microsoftonline.com/{organization}/adminconsent?client_id={client-id}`

Then, sign in with a Global Administrator account of the tenant where you are trying to access resources.
> **Note**
> - Replace `{organization}` with the tenant ID, for example, aaaaaaaaaaaa-bbbb-cccc-1111-22222222.
> - Replace `{client-id}` with the application ID, for example, dddddddddddd-eeee-ffff-3333-44444444.

## References

- [Understanding Microsoft Entra application consent experiences](/entra/identity-platform/application-consent-experience)
- [Overview of permissions and consent in the Microsoft identity platform](/entra/identity-platform/permissions-consent-overview)
- [Retire Service Principal-Less Authentication](/entra/identity-platform/retire-service-principal-less-authentication)


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/identity-of-calling-application-not-established) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
