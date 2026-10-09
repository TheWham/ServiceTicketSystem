# 将发出Microsoft Graph 请求的 Python 脚本检测为 Web 爬网程序

本文提供了在发出 Microsoft Graph 请求时可能会将 Python 脚本检测为 Web 爬网程序的问题的解决方案。

## 症状

网关有时可能会将发出 Microsoft Graph 请求的 Python 脚本检测为 Web 爬虫。 如果 Python 脚本使用池管理器，则阻止请求时会返回以下错误消息：

```
{'error': {'code': 'UnknownError', 'message': '\r\n403 Forbidden\r\n\r\n
403 Forbidden
\r\n
Microsoft-Azure-Application-Gateway/v2
\r\n\r\n\r\n', 'innerError': {'date': '{UTC Date/Time}', 'request-id': '{guid}', 'client-request-id': '{guid}'}}}
```

## 原因

之所以出现此问题，是因为某些 Python 脚本可能无法以符合预期模式的方式构建其请求。 因此，网关错误地将请求标识为来自 Web 爬网程序。

## 解决方案

若要解决此问题，请使用 [适用于 Python 的 Microsoft Graph SDK](https://github.com/microsoftgraph/msgraph-sdk-python-core)。 如果不想使用它，请使用 Python `Session` 的对象发送请求，以类似方式构造请求，就像 SDK 处理请求的方式一样。

下面是有关如何手动构造请求的示例：

```
from requests import Request, Session

def example_request(url):
    http = Session()
    req = Request('GET', url, headers=h)
    prepped = req.prepare()
    resp = http.send(prepped)
    return resp.json()
```

注释

- `User-Agent` HTTP 请求标头中的字符串应该对应用程序或脚本是唯一的，它与泛型流量不同。
- 包括其他标头，例如 `Accept: application/json` 有助于阐明请求的意图。
- 错误识别为爬虫流量可能导致 Microsoft 后端系统进行限流或采取其他自动化缓解措施。 正确标识客户端有助于避免这些问题。

如果使用其他 HTTP 客户端，请确保正确设置类似的标头。 请参阅 HTTP 客户端的文档，了解如何自定义请求标头。

## 详细信息

有关使用 Microsoft Graph 时的最佳做法的更多指南，请参阅以下文章：

- [使用 Microsoft Graph API](/zh-cn/graph/use-the-api)
- [Microsoft Graph限流指南](/zh-cn/graph/throttling)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/python-scripts-microsoft-graph-requests-detected-as-web-crawler)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
