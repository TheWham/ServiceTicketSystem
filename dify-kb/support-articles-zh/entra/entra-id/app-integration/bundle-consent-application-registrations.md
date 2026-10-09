# Microsoft Entra ID 应用程序的捆绑许可

## 概要

本文讨论如何为 Microsoft Entra ID 应用程序配置捆绑许可。

## 症状

你有一个自定义客户端应用和一个自定义 API 应用，并在 Microsoft Entra ID 中为这两个应用创建应用注册。 为这两个应用配置捆绑许可。 在此方案中，尝试登录到任一应用时，可能会收到以下错误消息之一：

- AADSTS70000：请求被拒绝，因为请求的一个或多个范围未经授权或已过期。 用户必须首先登录并授予客户端应用程序对请求的范围的访问权限。
- AADSTS650052：应用正在尝试访问服务“{app\_id}”（“app\_name”），但你的组织 %“{organization}”没有对该服务的服务主体。 请联系 IT 管理员，查看服务订阅的配置，或同意应用程序，以便创建所需的服务主体。

## 解决方案

### 步骤 1：为 API 应用程序注册配置 knownClientApplications

将自定义客户端应用 ID 添加到自定义 API 应用注册 `knownClientApplications` 的属性。 有关详细信息，请参阅 [knownClientApplications 属性](/zh-cn/entra/identity-platform/reference-app-manifest#knownclientapplications-attribute)。

### 步骤 2：配置 API 权限

请确保：

- 自定义客户端和自定义 API 应用注册上都正确配置了所有必需的 API 权限。
- 自定义客户端应用注册包括自定义 API 应用注册中定义的 API 权限。

### 步骤 3：登录请求

身份验证请求必须使用 `.default` Microsoft Graph 的范围。 对于Microsoft帐户，范围必须为自定义 API。

**Microsoft帐户和工作或学校帐户的示例请求**

```
https://login.microsoftonline.com/common/oauth2/v2.0/authorize
?response_type=code
&Client_id=00001111-aaaa-2222-bbbb-3333cccc4444
&redirect_uri=https://localhost
&scope=openid profile offline_access app_uri_id1/.default
&prompt=consent
```

注释

客户端似乎缺少 API 的权限。 此情况是预期的，因为客户端被列为`knownClientApplication`。

**仅限工作或学校账户的示例请求**

```
GET https://login.microsoftonline.com/common/oauth2/v2.0/authorize
?response_type=code
&client_id=00001111-aaaa-2222-bbbb-3333cccc4444
&redirect_uri=https://localhost
&scope=openid profile offline_access User.Read https://graph.microsoft.com/.default
&prompt=consent
```

#### 使用 MSAL.NET 实现

```
String[] consentScope = { "api://aaaabbbb-0000-cccc-1111-dddd2222eeee/.default" };
var loginResult = await clientApp.AcquireTokenInteractive(consentScope)
    .WithAccount(account)
	 .WithPrompt(Prompt.Consent)
      .ExecuteAsync();
```

新服务主体和权限的许可传播可能需要一些时间才能完成。 应用程序应成功处理此延迟。

#### 获取多个资源的令牌

如果客户端应用必须获取其他资源的令牌（如 Microsoft Graph），则必须实现逻辑，以便在用户同意应用程序后处理潜在的延迟。 以下是一些建议：

- 请求令牌时使用 `.default` 作用域。
- 跟踪获取的范围，直到返回所需的范围。
- 如果结果仍然没有达到所需的范围，请引入延迟。

目前，如果 `AcquireTokenSilent` 失败，MSAL 需要一个成功的交互式身份验证，然后才能允许再次进行无提示令牌的获取。 即使有效的刷新令牌可用，此限制也适用。

下面是使用重试逻辑的一些示例代码：

```
    public static async Task<AuthenticationResult> GetTokenAfterConsentAsync(string[] resourceScopes)
        {
            AuthenticationResult result = null;
            int retryCount = 0;

            int index = resourceScopes[0].LastIndexOf("/");

            string resource = String.Empty;

            // Determine resource of scope
            if (index < 0)
            {
                resource = "https://graph.microsoft.com";
            }
            else
            {
                resource = resourceScopes[0].Substring(0, index);
            }

            string[] defaultScope = { $"{resource}/.default" };

            string[] acquiredScopes = { "" };
            string[] scopes = defaultScope;
            
            while (!acquiredScopes.Contains(resourceScopes[0]) && retryCount <= 15)
            {
                try
                {
                    result = await clientApp.AcquireTokenSilent(scopes, CurrentAccount).WithForceRefresh(true).ExecuteAsync();
                    acquiredScopes = result.Scopes.ToArray();
                    if (acquiredScopes.Contains(resourceScopes[0])) continue;
                }
                catch (Exception e)
                { }

                // Switch scopes to pass to MSAL on next loop. This tricks MSAL to force AcquireTokenSilent after failure. This also resolves intermittent cachine issue in ESTS
                scopes = scopes == resourceScopes ? defaultScope : resourceScopes;
                retryCount++;

                // Obvisouly something went wrong
                if(retryCount==15)
                {
                    throw new Exception();
                }

                // MSA tokens do not return scope in expected format when .default is used
                int i = 0;
                foreach(var acquiredScope in acquiredScopes)
                {
                    if(acquiredScope.IndexOf('/')==0) acquiredScopes[i].Replace("/", $"{resource}/");
                    i++;
                }

                Thread.Sleep(2000);
            }

            return result;
        }
```

#### 关于使用代理流的自定义 API

与客户端应用类似，当自定义 API 尝试使用 On-Behalf-Of （OBO） 流获取另一资源的令牌时，同意后可能会立即失败。 若要解决此问题，可以实施重试逻辑和范围跟踪，如以下示例代码所示：

```
while (result == null && retryCount >= 6)
            {
                UserAssertion assertion = new UserAssertion(accessToken);
                try
                {
                    result = await apiMsalClient.AcquireTokenOnBehalfOf(scopes, assertion).ExecuteAsync();
                    
                }
                catch { }

                retryCount++;

                if (result == null)
                {
                    Thread.Sleep(1000 * retryCount * 2);
                }
            }

If (result==null) return new HttpStatusCodeResult(HttpStatusCode.Forbidden, "Need Consent");
```

如果所有重试失败，则返回错误消息，然后指示客户端启动完全同意过程。

**假设 API 引发 403 的客户端代码示例**

```
HttpResponseMessage apiResult = null;
apiResult = await MockApiCall(result.AccessToken);

if(apiResult.StatusCode==HttpStatusCode.Forbidden)
{
  var authResult = await clientApp.AcquireTokenInteractive(apiDefaultScope)
    .WithAccount(account)
    .WithPrompt(Prompt.Consent)
    .ExecuteAsync();
  CurrentAccount = authResult.Account;

  // Retry API call
  apiResult = await MockApiCall(result.AccessToken); 
}
```

## 建议和预期行为

理想情况下，你将创建一个单独的流来执行以下操作：

- 指导用户完成许可过程
- 在他们的租户或 Microsoft 帐户中预配应用程序和 API
- 在与登录分开的单个步骤中完成同意

如果不分隔此流，而是将其与应用的登录体验相结合，该过程可能会变得令人困惑。 用户可能会遇到多个同意提示。 若要改进体验，请考虑在应用中添加一条消息，告知用户他们可能要求他们多次同意：

- 对于Microsoft帐户，至少需要两个同意提示：一个用于客户端应用，一个用于 API。
- 通常，对于工作或学校帐户，只需要一个同意提示。

下面是一个端到端代码示例，演示了流畅的用户体验。 此代码仅在必要时支持所有帐户类型和提示同意。

```
string[] msGraphScopes = { "User.Read", "Mail.Send", "Calendar.Read" }
String[] apiScopes = { "api://aaaabbbb-0000-cccc-1111-dddd2222eeee/access_as_user" };
String[] msGraphDefaultScope = { "https://graph.microsoft.com/.default" };
String[] apiDefaultScope = { "api://aaaabbbb-0000-cccc-1111-dddd2222eeee/.default" };

var accounts = await clientApp.GetAccountsAsync();
IAccount account = accounts.FirstOrDefault();

AuthenticationResult msGraphTokenResult = null;
AuthenticationResult apiTokenResult = null;

try
{
	msGraphTokenResult = await clientApp.AcquireTokenSilent(msGraphScopes, account).ExecuteAsync();
	apiTokenResult = await clientApp.AcquireTokenSilent(apiScopes, account).ExecuteAsync();
}
catch (Exception e1)
{
	
	string catch1Message = e1.Message;
	string catch2Message = String.Empty;

	try
	{
        // First possible consent experience
		var result = await clientApp.AcquireTokenInteractive(apiScopes)
		  .WithExtraScopesToConsent(msGraphScopes)
		  .WithAccount(account)
		  .ExecuteAsync();
		CurrentAccount = result.Account;
		msGraphTokenResult = await clientApp.AcquireTokenSilent(msGraphScopes, CurrentAccount).ExecuteAsync();
		apiTokenResult = await clientApp.AcquireTokenSilent(apiScopes, CurrentAccount).ExecuteAsync();
	}
	catch(Exception e2)
	{
		catch2Message = e2.Message;
	};

	if(catch1Message.Contains("AADSTS650052") || catch2Message.Contains("AADSTS650052") || catch1Message.Contains("AADSTS70000") || catch2Message.Contains("AADSTS70000"))
	{
        // Second possible consent experience
		var result = await clientApp.AcquireTokenInteractive(apiDefaultScope)
			.WithAccount(account)
			.WithPrompt(Prompt.Consent)
			.ExecuteAsync();
		CurrentAccount = result.Account;
		msGraphTokenResult = await GetTokenAfterConsentAsync(msGraphScopes);
		apiTokenResult = await GetTokenAfterConsentAsync(apiScopes);
	}
}

// Call API

apiResult = await MockApiCall(apiTokenResult.AccessToken);
var contentMessage = await apiResult.Content.ReadAsStringAsync();

if(apiResult.StatusCode==HttpStatusCode.Forbidden)
{
	var result = await clientApp.AcquireTokenInteractive(apiDefaultScope)
		.WithAccount(account)
		.WithPrompt(Prompt.Consent)
		.ExecuteAsync();
	CurrentAccount = result.Account;

	// Retry API call
	apiResult = await MockApiCall(result.AccessToken);
}
```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/bundle-consent-application-registrations)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
