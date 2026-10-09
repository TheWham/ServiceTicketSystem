# 从 Python 应用使用 Fiddler 收集 HTTPS 流量

使用 Fiddler 捕获 Python 中的加密 HTTPS 网络流量可能具有挑战性，因为 Python 使用自己的受信任的证书存储而不是操作系统证书存储。 此外，默认情况下，Python 在某些方案中不使用代理。 本文介绍如何在不同方案中使用适用于 Python 应用的 Fiddler 捕获 SSL 流量。

## 适用于 Python 的 ADAL

使用 Fiddler 捕获集成 Azure Active Directory 身份验证库 （ADAL）的 Python 应用中的 HTTPS 流量时，可能会收到 SSL 错误消息。 出现此问题的原因是 Python 不信任 Fiddler 证书。 可以使用这两种方法中的任一方法来解决此问题。

注释

禁用 SSL 验证会带来安全风险。 应仅使用此方法进行故障排除。 不应在生产环境中使用它。

- 在初始化对象之前 `AuthenticationContext` ，在 Python 应用的开头设置环境变量：

  ```
  import os
  ...
  os.environ["ADAL_PYTHON_SSL_NO_VERIFY"] = "1"
  ```
- 将 `verify_ssl=False` 标志传递给 AuthenticationContext 方法：

  ```
  context = adal.AuthenticationContext(authority, verify_ssl=False)
  ```

## 适用于 Python 的 MSAL

将 Microsoft 身份验证库 （MSAL） 用于 Python 时，可以按如下所示禁用 SSL 验证：

```
app = msal.PublicClientApplication( client_id=appId, authority="https://login.microsoftonline.com/" + tenantId, verify=False )
```

## Python 请求模块

默认情况下，请求模块不使用代理。 您必须强制请求通过 Fiddler 代理，具体如下示例所示：

```
import requests

…
access_token = token.get('accessToken')
endpoint = "api_endpoint"
headers = {"Authorization": "Bearer " + access_token}
json_output = requests.get(
    endpoint,
    headers=headers,
    proxies={"http": "http://127.0.0.1:8888", "https": "http://127.0.0.1:8888"},
    verify=False
).json()
```

## 用于 Python 的 Azure Active Directory SDK （GraphRbacManagementClient）

以下示例演示如何禁用 SSL 验证：

```
from azure.graphrbac import GraphRbacManagementClient
from azure.common.credentials import UserPassCredentials

credentials = UserPassCredentials(
      <username>,    # Your user name
      <password>,    # Your password
      resource=”https://graph.windows.net”,
      verify=False
)
tenant_id = <tenant name or tenant id>
graphrbac_client = GraphRbacManagementClient(credentials, tenant_id)
graphrbac_client.config.connection.verify=False
res = graphrbac_client.users.get(<UPN or ObjectID>)
print(res.display_name)
```

**第三方信息免责声明**

本文讨论的第三方产品由独立于Microsoft的公司制造。 Microsoft对这些产品的性能或可靠性不作任何默示或其他保证。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/capture-https-traffic-fiddler-python-app)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
