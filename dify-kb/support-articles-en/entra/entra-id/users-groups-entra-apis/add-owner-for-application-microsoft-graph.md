# Add an owner to an application using Microsoft Graph

When an application is authenticated, you might want to be able to update its own properties such as the client secret or certificate. To do so, the application must be an owner of itself. You can implement this using the [Microsoft Graph API - Add owner](/graph/api/application-post-owners).

This article outlines the required permission and step-by-step instructions to add a service principal associated with an application as an owner of the application using Microsoft Graph.

## Required permission

The least privileged permissions for adding an owner to an application are described in the [Add owner - Permissions](/graph/api/application-post-owners#permissions) table. These permissions, such as `Application.ReadWrite.OwnedBy`, allow an application to manage applications of which it is an owner.

## Add an owner

Application owners can be individual users, the associated service principal, or another service principal. The following sections describe how to add the related service principal to an application as an owner.

### Step 1: Get the application's Object ID

To get the **Object ID** of the application you want to add an owner to, follow these steps:

1. Sign in to the [Azure portal](https://portal.azure.com).
2. Navigate to the Microsoft Entra admin center.
3. Browse to **Identity** > **Applications** > **App registrations**.
4. Locate the application and copy its **Object ID**.

     
*(image: Screenshot that shows an application's Object ID.)*

### Step 2: Get the owner (service principal's Object ID)

To get the **Object ID** of the service principal associated with the application, follow these steps:

1. Sign in to the [Azure portal](https://portal.azure.com).
2. Navigate to the Microsoft Entra admin center.
3. Browse to **Identity** > **Applications** > **Enterprise registrations**.
4. Locate the application and copy its **Object ID**.

    
*(image: Screenshot that shows an service principal's Object ID.)*

### Step 3: Add the owner to the application

Here're two methods to do this:

- [Method 1: Using Microsoft Graph Explorer](#method-1-using-microsoft-graph-explorer)
- [Method 2: Using Microsoft Graph PowerShell](#method-2-using-microsoft-graph-powershell)

#### Method 1: Using Microsoft Graph Explorer

1. Navigate to [Microsoft Graph Explorer](https://developer.microsoft.com/graph/graph-explorer).
2. Sign in with a user account that has the necessary permissions to update application owners, such as a Global Administrator or Application Administrator.
3. Use the following request:

    ```msgraph-interactive
    POST https://graph.microsoft.com/v1.0/applications/{application-object-id}/owners/$ref

    Content-Type: application/json

    {
        "@odata.id": "https://graph.microsoft.com/v1.0/directoryObjects/{service-principal-id}"
    }
    ```
> **Note**
    > Replace `{application-object-id}` with the **Object ID** of your application and `{service-principal-id}` with the **Object ID** of the service principal.

    Here's an example of what it looks like in Microsoft Graph Explorer:

    
*(image: Screenshot that shows a request in Microsoft Graph Explorer.)*

##### Troubleshoot Forbidden (403) error

You might encounter the following error during this process:

```output
"error": {
"code": "Authorization_RequestDenied",
"message": "Insufficient privileges to complete the operation.",
"innerError": {
"date": "2021-12-09T17:41:54",
"request-id": "b1909fc0-aa5c-4b43-8a1f-xxxxxxxxxxxx",
"client-request-id": "836e08bb-a12d-4ade-c761-xxxxxxxxxxxx"
}
}
```

To resolve the issue, consent to the API permission **Application.ReadWrite.All** for Microsoft Graph Explorer under the **Modify permissions** tab.

*(image: Screenshot that shows how to modify permission in Microsoft Graph Explorer.)*

#### Method 2: Using Microsoft Graph PowerShell

Here's an example of Microsoft Graph PowerShell scripts to add an owner to an application:

```powershell
Connect-MgGraph -Scopes Application.ReadWrite.All

# Owner
$OwnerServicePrincipalObjectId = "96858eb3-xxxx-xxxx-xxxx-33a6b0dc2430"

# Application to add owner to
$ApplicationObjectId = "b7463aa1-xxxx-xxxx-xxxx-0963d6c00485"

$Owner = @{
 "@odata.id" = "https://graph.microsoft.com/v1.0/directoryObjects/$($OwnerServicePrincipalObjectId)"
}

New-MgApplicationOwnerByRef -ApplicationId $ApplicationObjectId -BodyParameter $Owner
```


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/add-owner-for-application-microsoft-graph) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
