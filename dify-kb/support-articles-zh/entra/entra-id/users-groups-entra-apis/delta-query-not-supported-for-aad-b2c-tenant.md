# 在运行 Microsoft Graph 增量查询时，出现错误：“所请求的租户不支持更改枚举”

本文提供了在运行 Microsoft Graph 增量查询时发生的错误的解决方案。

## 症状

执行 [Microsoft Graph 增量查询](/zh-cn/graph/delta-query-overview)时`GET https://graph.microsoft.com/beta/users/delta`，可能会收到以下错误响应：

```
'error': {
'code': 'Request_UnsupportedQuery',
'message': 'Change enumeration is not supported for requested tenant.',
'innerError': {
'request-id': '<request-id>',
'date': '2020-05-22T13:17:45'
    }
}
```

## 原因

当租户是 [Azure Active Directory （AD） B2C](/zh-cn/azure/active-directory-b2c/overview) 租户时，会出现此问题。 目前，Azure AD B2C 租户无法使用差异或增量查询。

## 解决方案

在常规 Microsoft Entra 租户中运行增量查询。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/delta-query-not-supported-for-aad-b2c-tenant)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
