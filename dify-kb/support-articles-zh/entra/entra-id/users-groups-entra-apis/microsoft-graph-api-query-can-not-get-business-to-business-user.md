# Microsoft Graph API请求无法通过UPN获取B2B用户。

本文提供了解决在使用用户主体名称（UPN）执行Microsoft Graph API请求以获取企业间（B2B）用户时出现的错误的方法。

## 症状

在使用 UPN 执行 Microsoft Graph API 请求以获取 B2B 用户时，您可能会遇到错误。

请求示例：

`https://graph.microsoft.com/v1.0/users/example_gmail.com#EXT#@example.onmicrosoft.com`

响应示例：

```
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

## 原因

出现此问题的原因是 `#` UPN 中的字符被视为 URL 中的特殊字符。 之后 `#` 的所有内容都被视为片段，不会通过网络发送。

## 解决方案

若要解决此问题，必须将 UPN 中的字符编码 `#` 为 `%23`.

下面是正确的请求格式：

`https://graph.microsoft.com/v1.0/users/example_gmail.com%23EXT%23@example.onmicrosoft.com`

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/microsoft-graph-api-query-can-not-get-business-to-business-user)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
