# Microsoft Graph API requests fail to get B2B users using UPN

This article provides a solution to an error that occurs when you run a Microsoft Graph API request to get a Business-to-Business (B2B) user using User Principal Name (UPN).

## Symptoms

When you execute a Microsoft Graph API request to get a B2B user using UPN, you might encounter an error.

Request example:

`https://graph.microsoft.com/v1.0/users/example_gmail.com#EXT#@example.onmicrosoft.com`

Response exmaple:

```output
{
"error": {
"code": "Request_ResourceNotFound",
"message": "Resource '<resource-id>' does not exist or one of its queried reference-property objects are not present.",
"innerError": {
"request-id": "<request-id>",
"date": "2019-12-05T23:55:40"
            }
        }
}
```

## Cause

The issue occurs because the `#` character in the UPN is treated as a special character in the URL. Everything after the `#` is treated as a fragment and isn't sent over the wire.

## Solution

To resolve this issue, you must encode the `#` character in the UPN as `%23`.

Here's the correct request format:

`https://graph.microsoft.com/v1.0/users/example_gmail.com%23EXT%23@example.onmicrosoft.com`


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/microsoft-graph-api-query-can-not-get-business-to-business-user) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
