# 如何在访问令牌中显示组超额声明时获取已登录用户组列表

在应用程序的访问令牌中配置 `groups` 声明时，Microsoft Entra ID 具有可在访问令牌中返回的最大组数。 超出限制后，Azure 会提供组超额声明，该声明是可用于获取当前已登录用户的完整组列表的 URL。 此 URL 使用 Microsoft Graph 终结点。 有关声明的详细信息`groups`，请参阅[Microsoft 标识平台](/zh-cn/entra/identity-platform/access-tokens)中的 Access 令牌。

对于 JSON Web 令牌（JWT），Azure 会将令牌中存在的组数限制为 200。 为配置 `groups` 了声明的资源请求访问令牌时，如果你是 200 多个组的成员，你将获得组超额声明，而不是获取实际组。

本文介绍如何使用示例项目从组超额声明获取实际用户组列表。

## 为应用程序配置组声明

可以使用可选声明为应用程序配置 `groups` 声明。 有关详细信息，请参阅 [在 ID 令牌、访问令牌和 SAML 令牌](/zh-cn/entra/identity-platform/optional-claims)中配置和管理可选声明。

如果应用程序是第一方应用（Microsoft应用），则无法配置 `groups` 声明。 只能使用自己的应用注册对其进行配置。 如果要为客户端应用程序配置 `groups` 声明，则必须在 ID 令牌中对其进行配置。

## 下载示例项目

下载示例项目 [MSAL.Net\_GroupOveragesClaim](https://github.com/RayGHeld/MSAL.Net_GroupOveragesClaim)。 它演示如何从组超额声明获取组列表。

## 运行示例项目之前

- 为示例项目配置应用注册。

  示例项目将同时执行公共客户端流和机密客户端流，因此需要配置 Web 重定向（用于公共客户端流）和客户端密码（用于机密客户端流）。 由于机密客户端必须转到 `users` 终结点并基于用户 ID 查找组，因此可以从初始登录令牌获取这些组，因此机密客户端版本需要Microsoft Graph 应用程序权限 `Group.Read.All`。 公共客户端只是转到终结点， `me` 因为存在用户上下文。
- 将示例项目配置为使用租户，方法是使用适当的值更新 **appsettings.json** 文件：

  ```
  {
  "Azure": {
      "ClientId": "{client_id}",
      "TenantId": "{tenant_id}",
      "CallbackPath": "http://localhost",
      "ClientSecret": "{client_secret}",
      "AppScopes": [ "https://database.windows.net/.default" ],
      "GraphScopes": [ "User.Read" ]
  }
  }
  ```

  下面是appsettings.json**文件中设置**的说明：

  - `AppScopes`

    必须具有已为其配置声明的范围 `groups` 。

    通常，这是租户中的 API。 但在这种情况下，使用user\_impersonation权限添加Azure SQL 数据库适用于此方案。 已添加的范围适用于该 API。 这是因为 `groups` 已在该 API 上配置了声明。

    ![显示Azure SQL 数据库 API 的屏幕截图。](media/get-signed-in-users-groups-in-access-token/add-azure-sql-database.png)
  - `GraphScopes`

    添加应用程序权限 **Group.Read.All** （获取组显示名称所需的）和 **User.Read.All** （需要使用客户端凭据流获取组列表）。 必须为这些权限提供管理员同意。 委托的权限 **User.Read** 应已存在。 如果没有，请添加该元素。

    ![显示添加的应用程序权限的屏幕截图。](media/get-signed-in-users-groups-in-access-token/add-application-permissions.png)
  - 配置此示例项目的应用注册后，将客户端 ID（应用程序 ID）、客户端密码和租户 ID 添加到 **appsettings.json** 文件中。
- 在 **Create\_TestGroup.ps1.txt** 文件中运行 PowerShell 脚本以创建测试组（如果需要）。

  示例项目有一个名为 **Create\_TestGroup.ps1.txt**的文本文件。 若要在此文件中运行 PowerShell 脚本，请删除.txt扩展名。 在运行它之前，需要用户的对象 ID 才能添加到测试组。 你必须位于可以创建组并将用户添加到组的目录角色中。 示例项目将以格式`TEST_0001``TEST_0002`创建 255 个组，等等。 将添加你为每个组提供的对象 ID。 脚本结束时，它将登录到 Azure，运行命令以创建测试组，然后注销。

  备注

  第 53 行已注释掉示例清理方法：

  ```
  Connect-AzureAD
  Create-TestGroups -deleteIfExists $false
  #Delete-TestGroups
  Disconnect-AzureAD
  ```

## 使用组超额声明获取完整的用户组列表

1. 运行示例应用程序。
2. 登录到应用程序。

   身份验证在浏览器中发生，因为示例应用程序是 .NET 控制台应用程序。
3. 登录后，关闭浏览器，并返回到控制台应用程序。
4. 在控制台窗口中显示访问令牌后，将访问令牌复制到剪贴板，并将其粘贴到 <https://jwt.ms> 其中以查看编码的令牌。 这只是用户令牌。

   如果用户是组过多的成员，控制台窗口将显示原始组超额声明和该令牌的新组超额声明。 新的组超额声明将用于 .NET HTTP 客户端请求，而不是 Graph .NET SDK 请求。

   [![用于获取用户组完整列表的方法的屏幕截图。](media/get-signed-in-users-groups-in-access-token/select-method-to-get-groups.png)](media/get-signed-in-users-groups-in-access-token/select-method-to-get-groups.png#lightbox)
5. 选择要获取Microsoft Graph 的访问令牌类型。 可以使用当前已登录用户的用户令牌（刷新令牌流）或使用客户端凭据授予流获取访问令牌。
6. `.NET HTTP Request`选择或`Graph .NET SDK`获取用户组的完整列表。

   [![用于获取用户组完整列表的方法的屏幕截图。](media/get-signed-in-users-groups-in-access-token/select-method-to-get-groups.png)](media/get-signed-in-users-groups-in-access-token/select-method-to-get-groups.png#lightbox)

   组将显示在控制台窗口中：

   ![用户组的完整列表的屏幕截图。](media/get-signed-in-users-groups-in-access-token/groups-list.png)

## 关于代码

### Get\_GroupsOverageClaimURL 方法

示例项目使用 MSAL.NET （`Microsoft.Identity.Client`） 对用户进行身份验证并获取访问令牌。
`System.Net.Http` 用于 HTTP 客户端，Microsoft.Graph SDK 用于图形客户端。 若要分析 JSON 文件， `System.Text.Json` 请使用它。 若要从令牌中获取声明， `System.IdentityModel.Tokens.Jwt` 请使用。 提供程序 `JwtSecurityToken` 用于检索令牌中的组超额声明。

如果令牌包含声明 `claim_names` ，并且 `claim_sources`指示令牌中存在组超额声明。 在这种情况下，请使用用户 ID（oid）和两个声明来构造组列表的 URL，并在控制台窗口中输出原始值。 如果两个声明值之一不存在，该 `try/catch` 块将处理错误并返回一个 `string.empty` 值。 这表示令牌中没有组超额声明。

```
/// <summary>
		/// Looks for a group overage claim in an access token and returns the value if found.
		/// </summary>
		/// <param name="accessToken"></param>
		/// <returns></returns>
		private static string Get_GroupsOverageClaimURL(string accessToken)
        {
			JwtSecurityToken token = new JwtSecurityTokenHandler().ReadJwtToken(accessToken);
			string claim = string.Empty;
			string sources = string.Empty;
			string originalUrl = string.Empty;
			string newUrl = string.Empty;

            try
            {
				// use the user id in the new graph URL since the old overage link is for Azure AD Graph which is being deprecated.
				userId = token.Claims.First(c => c.Type == "oid").Value;

				// getting the claim name to properly parse from the claim sources but the next 3 lines of code are not needed,
				// just for demonstration purposes only so you can see the original value that was used in the token.
				claim = token.Claims.First(c => c.Type == "_claim_names").Value;
				sources = token.Claims.First(c => c.Type == "_claim_sources").Value;
				originalUrl = sources.Split("{\"" + claim.Split("{\"groups\":\"")[1].Replace("}","").Replace("\"","") + "\":{\"endpoint\":\"")[1].Replace("}","").Replace("\"", "");
				
				// make sure the endpoint is specific for your tenant -- .gov for example for gov tenants, etc.
				newUrl = $"https://graph.microsoft.com/v1.0/users/{userId}/memberOf?$orderby=displayName&$count=true";

				Console.WriteLine($"Original Overage URL: {originalUrl}");
				//Console.WriteLine($"New URL: {newUrl}");

			} catch {
				// no need to do anything because the claim does not exist
			} 

			return newUrl;
        }
```

### Program.cs 文件

在此文件中，有一个用于用户登录和获取访问令牌的公共客户端应用程序配置，以及用于应用程序登录和获取访问令牌的机密客户端应用程序（客户端凭据授予流）。
`ManualTokenProvider` 用于 Graph 服务客户端将访问令牌传递给服务，而不是让 Graph 获取它。

还有一个appsettings.json**文件和一个**类（**AzureConfig.cs**），用于在运行时存储这些设置。 公共静态属性 `AzureSettings` 使用配置生成器从配置文件中检索设置，类似于 ASP.NET Core 应用程序。 此功能必须添加，因为它不是控制台应用程序的本机功能。

```
static AzureConfig _config = null;
		public static AzureConfig AzureSettings
		{
			get
			{
				// Only load this when the app starts.
				// To reload, you will have to set the variable _config to null again before calling this property.
				if (_config == null)
				{
					_config = new AzureConfig();
					IConfiguration builder = new ConfigurationBuilder()
						.SetBasePath(System.IO.Directory.GetCurrentDirectory())
						.AddJsonFile("appsettings.json", optional: true, reloadOnChange: true)
						.Build();

					ConfigurationBinder.Bind(builder.GetSection("Azure"), _config);
				}

				return _config;
			}
		}
```

### 验证提供程序

对于 Graph 服务客户端的 `Authentication` 提供程序，示例项目使用自定义手动令牌提供程序为已使用 MSAL 获取访问令牌的客户端设置访问令牌。

```
using Microsoft.Graph;

using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading.Tasks;

namespace MSAL.Net_GroupOveragesClaim.Authentication
{
    class ManualTokenProvider : IAuthenticationProvider
    {
        string _accessToken;

        public ManualTokenProvider ( string accessToken)
        {
            _accessToken = accessToken;
        }

        async Task IAuthenticationProvider.AuthenticateRequestAsync(HttpRequestMessage request)
        {
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _accessToken);
            request.Headers.Add("ConsistencyLevel", "eventual");
        }
    }
}
```

### Get\_Groups\_HTTP\_Method

此方法调用 `Graph_Request_viaHTTP` 该方法以获取组列表，然后在控制台窗口中显示该列表。

```
/// <summary>
		/// Entry point to make the request to Microsoft graph using the .Net HTTP Client
		/// </summary>
		/// <param name="graphToken"></param>
		/// <returns></returns>
		private static async Task Get_Groups_HTTP_Method(string graphToken, string url)
        {
			List<Group> groupList = new List<Group>();
						
			groupList = await Graph_Request_viaHTTP(graphToken, url);
			foreach (Group g in groupList)
			{
				Console.WriteLine($"Group Id: {g.Id} : Display Name: {g.DisplayName}");
			}
		}
```

```
/// <summary>
		/// Calls Microsoft Graph via a HTTP request.  Handles paging in the request
		/// </summary>
		/// <param name="user_access_token"></param>
		/// <returns>List of Microsoft Graph Groups</returns>
		private static async Task<List<Group>> Graph_Request_viaHTTP(string user_access_token, string url)
        {
			string json = string.Empty;
			//string url = "https://graph.microsoft.com/v1.0/me/memberOf?$orderby=displayName&$count=true";
			List<Group> groups = new List<Group>();

			// todo: check for the count parameter in the request and add if missing

			/*
			 * refer to this documentation for usage of the http client in .net
			 * https://docs.microsoft.com/en-us/dotnet/api/system.net.http.httpclient?view=net-5.0
			 * 
			 */

			// add the bearer token to the authorization header for this request
			_httpClient.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue( "Bearer", user_access_token);
			
			// adding the consistencylevel header value if there is a $count parameter in the request as this is needed to get a count
			// this only needs to be done one time so only add it if it does not exist already.  It is case sensitive as well.
			// if this value is not added to the header, the results will not sort properly -- if that even matters for your scenario
			if(url.Contains("&$count", StringComparison.OrdinalIgnoreCase))
            {
                if (!_httpClient.DefaultRequestHeaders.Contains("ConsistencyLevel"))
                {
					_httpClient.DefaultRequestHeaders.Add("ConsistencyLevel", "eventual");
                }
            }
			
			// while loop to handle paging
			while(url != string.Empty)
            {
				HttpResponseMessage response = await _httpClient.GetAsync(new Uri(url));
				url = string.Empty; // clear now -- repopulate if there is a nextlink value.

				if (response.IsSuccessStatusCode)
				{
					json = await response.Content.ReadAsStringAsync();

					// Console.WriteLine(json);

					using (JsonDocument document = JsonDocument.Parse(json))
					{
						JsonElement root = document.RootElement;
						// check for the nextLink property to see if there is paging that is occuring for our while loop
						if (root.TryGetProperty("@odata.nextLink", out JsonElement nextPage))
                        {
							url = nextPage.GetString();
                        }
						JsonElement valueElement = root.GetProperty("value"); // the values

						// loop through each value in the value array
						foreach (JsonElement value in valueElement.EnumerateArray())
						{
							if (value.TryGetProperty("@odata.type", out JsonElement objtype))
							{
								// only getting groups -- roles will show up in this graph query as well.
								// If you want those too, then remove this if filter check
								if (objtype.GetString() == "#microsoft.graph.group")
								{
									Group g = new Group();

									// specifically get each property you want here and populate it in our new group object
									if (value.TryGetProperty("id", out JsonElement id)) { g.Id = id.GetString(); }
									if (value.TryGetProperty("displayName", out JsonElement displayName)) { g.DisplayName = displayName.GetString(); }

									groups.Add(g);
								}
							}
						}
					}
				} else
                {
					Console.WriteLine($"Error making graph request:\n{response.ToString()}");
                }
			} // end while loop
	
			return groups;
        }
```

### Get\_Groups\_GraphSDK\_Method

同样，Graph SDK 有一个入口方法 `Get_Groups_GraphSDK_Method`。 此方法调用 `Get_GroupList_GraphSDK` 获取组列表，然后在控制台窗口中显示它。

```
/// <summary>
		/// Entry point to make the request to Microsoft Graph using the Graph SDK and outputs the list to the console.
		/// </summary>
		/// <param name="graphToken"></param>
		/// <returns></returns>
		private static async Task Get_Groups_GraphSDK_Method(string graphToken, bool me_endpoint)
        {
			List<Group> groupList = new List<Group>();

			groupList = await Get_GroupList_GraphSDK(graphToken, me_endpoint);
			foreach (Group g in groupList)
			{
				Console.WriteLine($"Group Id: {g.Id} : Display Name: {g.DisplayName}");
			}
		}
```

### Get\_GroupList\_GraphSDK方法

此方法确定是使用 `me` 终结点还是 `users` 终结点来获取组列表。 如果使用客户端凭据授予流来获取 Microsoft Graph 的访问令牌，请使用 `me` 终结点。 如果没有（例如，委托流用于访问令牌），请使用 `users` 终结点。 无论使用哪种方法，代码都会处理分页，因为默认情况下，每个页面只返回 100 条记录。 分页是通过值确定的 `@odata.nextLink` 。 如果该属性有一个值，则会为下一页的数据调用完整的 URL。 有关分页的详细信息，请参阅 [应用中](/zh-cn/graph/paging)的分页Microsoft图形数据。

```
/// <summary>
		/// Calls the Me.MemberOf endpoint in Microsoft Graph and handles paging
		/// </summary>
		/// <param name="graphToken"></param>
		/// <returns>List of Microsoft Graph Groups</returns>
		private static async Task<List<Group>> Get_GroupList_GraphSDK(string graphToken, bool use_me_endpoint)
        {

			GraphServiceClient client;

			Authentication.ManualTokenProvider authProvider = new Authentication.ManualTokenProvider(graphToken);

			client = new GraphServiceClient(authProvider);
			IUserMemberOfCollectionWithReferencesPage membershipPage = null;

			HeaderOption option = new HeaderOption("ConsistencyLevel","eventual");

			if (use_me_endpoint)
            {
                if (!client.Me.MemberOf.Request().Headers.Contains(option))
                {
					client.Me.MemberOf.Request().Headers.Add(option);
                }

				membershipPage = await client.Me.MemberOf
					.Request()
					.OrderBy("displayName&$count=true") // todo: find the right way to add the generic query string value for count
					.GetAsync();
            } else
            {
                if (!client.Users[userId].MemberOf.Request().Headers.Contains(option))
                {
					client.Users[userId].MemberOf.Request().Headers.Add(option);
                }

				membershipPage = await client.Users[userId].MemberOf
					.Request()
					.OrderBy("displayName&$count=true")
					.GetAsync();
            }

			List<Group> allItems = new List<Group>();			
			
			if(membershipPage != null)
            {
				foreach(DirectoryObject o in membershipPage)
                {
					if(o is Group)
                    {
						allItems.Add((Group)o);
                    }
                }

				while (membershipPage.AdditionalData.ContainsKey("@odata.nextLink") && membershipPage.AdditionalData["@odata.nextLink"].ToString() != string.Empty)
                {
					membershipPage = await membershipPage.NextPageRequest.GetAsync();
					foreach (DirectoryObject o in membershipPage)
					{
						if (o is Group)
						{
							allItems.Add(o as Group);
						}
					}
				}

            }

             return allItems;

		}
```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/get-signed-in-users-groups-in-access-token)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
