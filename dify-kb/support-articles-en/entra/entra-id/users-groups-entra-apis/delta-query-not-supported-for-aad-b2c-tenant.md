# Error "Change enumeration is not supported for requested tenant" when running a Microsoft Graph delta query

This article provides a solution to an error that occurs when you run a Microsoft Graph delta query.

## Symptoms

When executing a [Microsoft Graph delta query](/graph/delta-query-overview), such as `GET https://graph.microsoft.com/beta/users/delta`, you might receive the following error response:

```output
'error': {
'code': 'Request_UnsupportedQuery',
'message': 'Change enumeration is not supported for requested tenant.',
'innerError': {
'request-id': '<request-id>',
'date': '2020-05-22T13:17:45'
    }
}
```

## Cause

This issue occurs when your tenant is an [Azure Active Directory (AD) B2C](/azure/active-directory-b2c/overview) tenant. Currently, differential or delta queries aren't supported in Azure AD B2C tenants.

## Solution

Run a delta query in a regular Microsoft Entra tenant.


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/delta-query-not-supported-for-aad-b2c-tenant) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
