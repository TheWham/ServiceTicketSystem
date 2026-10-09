# "Neither tenant is B2C or tenant doesn't have premium license" error when you query sign-in activities

This article discusses the error that occurs when you make Microsoft Graph API calls that are related to user sign-in activities or user registration details.

## Symptoms

You run one of the following Microsoft Graph API calls:

```http
GET https://graph.microsoft.com/v1.0/auditLogs/signIns

GET https://graph.microsoft.com/v1.0/users?$select=displayName,userPrincipalName,signInActivity

GET https://graph.microsoft.com/v1.0/reports/UserRegistrationDetails
```

After you run the call, your receive an error response that resembles the following text:

```output
'error': {
    'code': 'Authentication\_RequestFromNonPremiumTenantOrB2CTenant',
    'message': 'Neither tenant is B2C or tenant doesn't have premium license',
    'innerError': {
        'date': '2021-03-04T07:53:51',
        'request-id': 'a0a074e6-xxx-c511669fa420',
        'client-request-id': 'a0a074e6-xxx-c511669fa420'
    }
}
```

## Solution

### Scenario 1: Query user sign-in activities

1. Make sure that the target tenant has an Entra ID Premium P1 or P2 license. In the Azure portal, go to **Microsoft Entra ID**, select **Overview**, and then check the **License** value.  For more information, see [Sign up for Microsoft Entra ID P1 or P2 editions](/entra/fundamentals/get-started-premium).
1. Verify that the Microsoft Graph Access Token was granted the `AuditLog.Read.All` and `Directory.Read.All` permissions.

### Scenario 2: Query credential user registration details

1. Make sure that the target tenant has an Entra ID Premium P1 or P2 license.
1. Verify that the Microsoft Graph Access Token was granted the `Reports.Read.All` permission.
1. Verify that the authenticating user or the service principle of the application is in one of the following required administrative roles:
    - Reports Reader
    - Security Reader
    - Security Administrator
    - Global Reader
    - Global Administrator

## More information

If an application is configured by using only the **AuditLog.Read.All** permission, this error might occur intermittently. This is expected behavior because the **Directory.Read.All** permission is required to retrieve tenant licensing information if it isn't already cached. To avoid this error, make sure that both permissions are included.


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/b2c-or-tenant-premium-license-sign-in-activities) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
