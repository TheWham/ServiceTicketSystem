# 使用托管标识在 VB.Net 和 C 中调用Microsoft图形 API#

本文介绍如何使用托管标识获取访问令牌，以便在 VB.Net 和 C# 中调用 Microsoft Graph API。

## 为托管标识配置权限

所有托管标识（用户分配或系统分配）都将具有显示在“企业应用”边栏选项卡中的服务主体。 若要获取这些标识上Microsoft Graph 的权限，必须授予 OAuth 权限。 为此，请运行以下 PowerShell 脚本：

```
# Your tenant id (in Azure Portal, under Azure Active Directory -> Overview )
$TenantID = "{your tenant id}"

# Name of the manage identity
$DisplayNameOfApp = "{your managed identity name}" 

# Check the Microsoft Graph documentation for the permission you need for the operation
$Permissions = @("User.Read.All")
 
# Main script

# Microsoft Graph App ID
$MSGraphAppId = "00000003-0000-0000-c000-000000000000"

# Uncomment the next line if you need to Install the module (You need admin on the machine)
# Install-Module Microsoft.Graph
Connect-MgGraph -TenantId $TenantID -scopes Application.ReadWrite.All

# Get the application we want to modify
$sp = (Get-MgServicePrincipal -Filter "displayName eq '$DisplayNameOfApp'")
  
# If assigning MS Graph Permissions
$GraphServicePrincipal = Get-MgServicePrincipal -Filter "appId eq '$MSGraphAppId'"
 
# Add permissions
foreach($permission in $Permissions)
{
 $AppRole = $GraphServicePrincipal.AppRoles | Where-Object {$_.Value -eq $permission -and $_.AllowedMemberTypes -contains "Application"}

  New-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $sp.Id -PrincipalId $sp.Id -ResourceId $GraphServicePrincipal.Id -AppRoleId $AppRole.Id
}

<# Remove permissions - this portion of the script show how to remove those same permissions
$AppRoleAssignments = Get-MgServiceAppRoleAssignedTo -ObjectId $sp.ObjectId

foreach($permission in $Permissions)
{

  $AppRole = $GraphServicePrincipal.AppRoles | Where-Object {$_.Value -eq $permission -and $_.AllowedMemberTypes -contains "Application"}

 foreach($AppRoleAssignment in $AppRoleAssignments)
   {
      if($AppRole.Id -eq $AppRoleAssignment.Id) {
         Remove-MgServiceAppRoleAssignment -ObjectId $sp.ObjectId -AppRoleAssignmentId $AppRoleAssignment.objectid
      }
      
   }
}
#>
```

## 获取访问令牌

在服务主体中配置权限后，从以下资源发出令牌请求： `https://graph.microsoft.com`

备注

为资源发出令牌请求后，将在接下来的 24 小时内获得相同的令牌，即使你进行了权限更改。 若要将令牌与任何新权限一起获取，必须等待当前令牌过期。

```
Dim at As AccessToken = credential.GetToken(New TokenRequestContext(New String() {"https://graph.microsoft.com"}))
```

```
AccessToken at = credential.GetToken(new TokenRequestContext(new string[] { "https://graph.microsoft.com" }));
```

## 调用图形 API

此示例演示如何为资源（如 Microsoft Graph）请求访问令牌。 在代码中使用 Microsoft Graph 服务客户端时，无需显式指定资源，因为Microsoft Graph 服务客户端会自动处理该资源。 在 VB.Net 中，必须添加 `Microsoft.Graph` NuGet 包，然后添加 `Imports Microsoft.Graph` 代码文件的顶部。

### VB.Net

```
    Sub Main()

        Do While True
            Get_AccessToken_With_UserAssigned_MSI()
            Make_GraphRequest_withUserMSI_Token()
            Get_Secret_With_UserAssigned_MSI()

            Get_AccessToken_With_SystemAssigned_MSI()
            Get_Secret_With_SystemAssigned_MSI()
            Make_GraphRequest_withSystemMSI_Token()

            Console.WriteLine("Press Enter to try again or any other key to exit")
            Dim key As ConsoleKeyInfo = Console.ReadKey()

            If Not key.Key = ConsoleKey.Enter Then
                Return
            End If
        Loop

    End Sub

    Sub Get_AccessToken_With_UserAssigned_MSI()
        Console.WriteLine($"Getting access token with user assigned msi:")

        Dim credential As New ManagedIdentityCredential(userAssignedClientId)

        Dim at As AccessToken = credential.GetToken(New TokenRequestContext(New String() {"https://graph.microsoft.com"}))
        Dim accessToken As String = at.Token.ToString()
        Console.WriteLine($"Access Token = {accessToken}")

    End Sub

    Sub Make_GraphRequest_withUserMSI_Token()
        Console.WriteLine($"Making graph request with User MSI Token:")

        Dim credential As New ManagedIdentityCredential(userAssignedClientId)

        Dim graphClient As New GraphServiceClient(credential)

        Dim users As IGraphServiceUsersCollectionPage
        Try
            users = graphClient.Users().Request.GetAsync().Result
            Console.WriteLine($"Number of users in tenant: {users.Count}{vbCrLf}")
        Catch ex As Exception
            Console.WriteLine($"Exception: {ex.Message}")
        End Try

    End Sub

    Sub Get_AccessToken_With_SystemAssigned_MSI()
        Console.WriteLine($"Getting access token with system assigned msi:")

        Dim credential As New ManagedIdentityCredential()
        Dim at As AccessToken = credential.GetToken(New TokenRequestContext(New String() {"https://graph.microsoft.com"}))

        Dim accessToken As String = at.Token.ToString()
        Console.WriteLine($"Access Token = {accessToken}")
    End Sub

    Sub Make_GraphRequest_withSystemMSI_Token()
        Console.WriteLine($"Making graph request with system MSI token:")

        Dim credential As New ManagedIdentityCredential()

        Dim graphClient As New GraphServiceClient(credential)

        Dim users As IGraphServiceUsersCollectionPage
        Try
            users = graphClient.Users().Request.GetAsync().Result
            Console.WriteLine($"Number of users in tenant: {users.Count}{vbCrLf}")
        Catch ex As Exception
            Console.WriteLine($"Exception: {ex.Message}")
        End Try

    End Sub
```

### C#

```
        static void Main(string[] args)
        {
            while (true)
            {
                Console.Clear();

                Get_AccessToken_With_UserAssigned_MSI();
                Get_Secret_With_UserAssigned_MSI();
                Make_GraphRequest_With_UserMSI_Token();

                Get_AccessToken_With_SystemAssigned_MSI();
                Get_Secret_With_SystemAssigned_MSI();
                Make_GraphRequest_With_SystemMSI_Token();

                Console.WriteLine("Press Enter to try again or any other key to exit");
                ConsoleKeyInfo key = Console.ReadKey();
                if (key.Key != ConsoleKey.Enter)
                {
                    return;
                }
            }

        }

        static void Get_AccessToken_With_UserAssigned_MSI()
        {
            Console.WriteLine($"Getting access token with user assigned msi:");

            ManagedIdentityCredential credential = new ManagedIdentityCredential(userAssignedClientId);

            AccessToken at = credential.GetToken(new TokenRequestContext(new string[] { "https://database.windows.net" }));
            string accessToken = at.Token;

            Console.WriteLine($"Access Token = {accessToken}");

        }

        static void Get_AccessToken_With_SystemAssigned_MSI()
        {
            Console.WriteLine($"Getting access token with system assigned msi:");

            ManagedIdentityCredential credentail = new ManagedIdentityCredential();

            AccessToken at = credentail.GetToken(new TokenRequestContext(new string[] { "https://database.windows.net" }));
            string accessToken = at.Token;

            Console.WriteLine($"Access token = {accessToken}");

        }

        static void Make_GraphRequest_With_UserMSI_Token()
        {
            Console.WriteLine($"Making graph request with User MSI Token:");

            ManagedIdentityCredential credential = new ManagedIdentityCredential(userAssignedClientId);
            GraphServiceClient graphClient = new GraphServiceClient(credential);

            IGraphServiceUsersCollectionPage users;

            try
            {
                users = graphClient.Users.Request().GetAsync().Result;
                Console.WriteLine($"Number of users in tenant: {users.Count}\n");
            } catch(Exception ex)
            {
                Console.WriteLine($"\nException: {ex.InnerException.Message}");
            }

        }

        static void Make_GraphRequest_With_SystemMSI_Token()
        {
            Console.WriteLine($"Making graph request with system MSI Token:");

            ManagedIdentityCredential credential = new ManagedIdentityCredential();
            GraphServiceClient graphClient = new GraphServiceClient(credential);

            IGraphServiceUsersCollectionPage users;

            try
            {
                users = graphClient.Users.Request().GetAsync().Result;
                Console.WriteLine($"Number of users in tenant: {users.Count}\n");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"\nException: {ex.InnerException.Message}");
            }
```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/call-graph-api-using-managed-dentities)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
