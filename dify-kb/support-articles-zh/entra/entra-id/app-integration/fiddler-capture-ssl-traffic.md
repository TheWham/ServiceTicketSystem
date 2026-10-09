# 使用 Fiddler 捕获 SSL 流量

本文提供有关使用 Fiddler 捕获安全套接字层 （SSL） 流量以排查 Microsoft Entra 应用问题的说明。

## 方案 1：使用 Fiddler 捕获 Node.js Web 流量

若要使用 Fiddler 捕获 Node.js Web 应用程序流量，需要通过 Fiddler 代理 Node.js 请求。 默认代理为 127.0.0.1：8888。 为此，在 `npm start` 运行命令以启动 Node.js 服务器之前，请运行以下命令来启用代理设置：

```
set https_proxy=http://127.0.0.1:8888
set http_proxy=http://127.0.0.1:8888
set NODE_TLS_REJECT_UNAUTHORIZED=0
```

注释

若要了解 Fiddler 正在侦听的端口，请从 Fiddler 菜单中选择 **“工具**>**选项**>**连接** ”。

## 方案 2：使用 Fiddler 捕获 Azure Key Vault 机密信息客户端（来自适用于 .NET 的 Azure SDK）

若要使用 Fiddler 捕获 Azure Key Vault 流量，请将 Fiddler 设置为代理，方法是在应用程序代码中设置 `http_proxy` 环境变量 `https_proxy` ，如下所示：

```
using Azure.Identity;
using Azure.Security.KeyVault.Secrets;
...
// add these lines in your method to call Azure Key Vault
Environment.SetEnvironmentVariable("HTTP_PROXY", "http://127.0.0.1:8888");
Environment.SetEnvironmentVariable("HTTPS_PROXY", "http://127.0.0.1:8888");

var client = new SecretClient(new Uri(keyVaultUrl), credential);
KeyVaultSecret result = client.GetSecret("MySecret");
```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/fiddler-capture-ssl-traffic)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
