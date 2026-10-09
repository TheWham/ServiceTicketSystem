# 使用 Invoke-RestMethod 处理Microsoft图形 API 请求中的错误

本文提供了一个代码示例，演示如何在 PowerShell 中使用 `Invoke-RestMethod` cmdlet 向 Microsoft Graph API 发出请求时处理错误并实现重试逻辑。

## 先决条件

- 使用客户端密码注册 Azure 应用
- `user.read.all` azure 应用的 Microsoft.Graph 权限。 有关详细信息，请参阅 [列表用户](/zh-cn/graph/api/user-get?view=graph-rest-1.0&tabs=http&preserve-view=true)。

## 代码示例

为了演示重试逻辑，此示例尝试查询 `signInActivity` 来宾用户的数据。 运行此代码时，可能会收到“403”错误。

- **Get-AccessTokenCC** 此函数从 Microsoft Entra ID（前 Azure Active Directory）请求访问令牌。 令牌将用于对Microsoft Graph 的 API 请求进行身份验证。 必须提供 Azure 注册应用的值`$clientSecret``$clientId`和`$tenantId`变量。
- **Get-GraphQueryOutput （$Uri）** 此函数向 Microsoft 图形 API 发出检索数据的请求。 它还处理分页。 如果生成了“403”错误，该函数将重试请求。

```
Function Get-AccessTokenCC
 
{
    $clientSecret = ''
    $clientId = ''
    $tenantId = ''
    # Construct URI
    $uri = "https://login.microsoftonline.com/$tenantId/oauth2/v2.0/token"
    # Construct Body
    $body = @{
        client_id = $clientId
        client_secret = $clientSecret
        scope = 'https://graph.microsoft.com/.default'
        grant_type = 'client_credentials'
    }
    # Get OAuth 2.0 Token
    $tokenRequest = Invoke-WebRequest -Method Post -Uri $uri -ContentType 'application/x-www-form-urlencoded' -Body $body -UseBasicParsing
    # Access Token
    $token = ($tokenRequest.Content | ConvertFrom-Json).access_token
    #$token = "Junk"  #uncomment this line to cause a 401 error -- you can set that status in the error handler to test the pause and retry
    #Write-Host "access_token = $token"
    return $token
}
 
Function Get-GraphQueryOutput ($Uri)
{
    write-host "uri = $Uri"
    write-host "token = $token"

    $retryCount = 0
    $maxRetries = 3
    $pauseDuration = 2
 
    $allRecords = @()
    while ($Uri -ne $null){
        Write-Host $Uri
        try {
            # todo: verify that the bearer token is still good -- hasn't expired yet -- if it has, then get a new token before making the request
            $result=Invoke-RestMethod -Method Get -Uri $Uri -ContentType 'application/json' -Headers @{Authorization = "Bearer $token"}
           
            Write-Host $result
         
            if($query.'@odata.nextLink'){
                # set the url to get the next page of records. For more information about paging, see https://docs.microsoft.com/graph/paging
                $Uri = $query.'@odata.nextLink'
            } else {
                $Uri = $null
            }
 
        } catch {
            Write-Host "StatusCode: " $_.Exception.Response.StatusCode.value__
            Write-Host "StatusDescription:" $_.Exception.Response.StatusDescription
 
            if($_.ErrorDetails.Message){
                Write-Host "Inner Error: $_.ErrorDetails.Message"
            }
 
            # check for a specific error so that we can retry the request otherwise, set the url to null so that we fall out of the loop
            if($_.Exception.Response.StatusCode.value__ -eq 403 ){
                # just ignore, leave the url the same to retry but pause first
                if($retryCount -ge $maxRetries){
                    # not going to retry again
                    $Uri = $null
                    Write-Host 'Not going to retry...'
                } else {
                    $retryCount += 1
                    Write-Host "Retry attempt $retryCount after a $pauseDuration second pause..."
                    Start-Sleep -Seconds $pauseDuration
                }
 
            } else {
                # not going to retry -- set the url to null to fall back out of the while loop
                $Uri = $null
            }
        }
    }
 
    $output = $allRecords | ConvertTo-Json

if ($result.PSObject.Properties.Name -contains "value") {
    return $result.value
} else {
    return $result
}
}
 
# Graph API URIs
$uri = 'https://graph.microsoft.com/v1.0/users?$filter=userType eq ''Guest''&$select=displayName,UserprincipalName,userType,identities,signInActivity'

# Pull Data
$token = Get-AccessTokenCC
Get-GraphQueryOutput -Uri $uri|out-file c:\\temp\\output.json
```

## 捕获特定标头

对于高级方案，例如捕获特定标头值（例如 `Retry-After` 在限制响应期间（HTTP 429），请使用：

```
$retryAfterValue = $_.Exception.Response.Headers["Retry-After"]
```

若要处理“429 - 请求过多”错误，请参阅 [Microsoft图形限制指南](/zh-cn/graph/throttling)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/graph-api-error-handling-invoke-restmethod)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
