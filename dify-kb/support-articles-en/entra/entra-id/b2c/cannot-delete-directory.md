# Error when you try to delete a B2C directory in Microsoft Entra ID: Cannot delete '\<contoso>'

This article describes an issue in which an error occurs when you try to delete a B2C directory in Microsoft Entra ID.

_Original product version:_ &nbsp; Microsoft Entra ID  
_Original KB number:_ &nbsp; 3112170

## Symptoms

In a Microsoft Entra environment, you set up a B2C directory, and then you try to delete it. However, you receive the following error message:

> Cannot delete '\<contoso>'  
The following issue(s) prevent deletion of the directory:  
Directory contains one or more applications that were added by a user or administrator

## Cause

This problem occurs if existing B2C application service principals (for example, CPIM, Ibiza Portal, and SSPR) are blocking the deletion.

## Resolution

To fix this issue, use the Azure portal.

### Step 1: Delete all apps that are listed on the Azure AD B2C Dashboard

To do this, follow these steps:

1. Sign in [Azure portal](https://portal.azure.com/) as an administrator who has access to the Azure AD B2C directory.
2. Select your display name in the upper-right corner, and then select the directory that's your B2C directory.
> **Note**
    > If you have only one directory, your Azure AD B2C directory will already be selected.

3. To find the Azure AD B2C blade, select the More Services **(>)** button in the lower-left corner, and then search on "B2C".
4. Select **Azure AD B2C**.
5. Select **All Settings**, and then select **Applications**.

    
*(image: Screenshot of applications setting.)*

6. Delete all applications. To do this, select the application, select **Properties**, and then select the **Delete** button.

    
*(image: Screenshot shows how to delete an app.)*

### Step 2: Delete the Azure AD B2C tenant

To do this, follow these steps:

1. In the Azure AD B2C directory, locate and select the **Microsoft Entra ID** blade in the Azure portal.
2. On the **Overview** menu, select **Delete Directory**.

3. Follow the instructions in the portal.


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/b2c/cannot-delete-directory) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
