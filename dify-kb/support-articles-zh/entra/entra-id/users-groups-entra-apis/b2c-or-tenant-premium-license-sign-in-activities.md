# 查询登录活动时出现“租户不是 B2C，或者租户没有高级许可证”错误

本文讨论在进行与用户登录活动或用户注册详细信息相关的 Microsoft Graph API 调用时发生的错误。

## 症状

您运行以下 Microsoft Graph API 调用之一：

```
GET https://graph.microsoft.com/v1.0/auditLogs/signIns

GET https://graph.microsoft.com/v1.0/users?$select=displayName,userPrincipalName,signInActivity

GET https://graph.microsoft.com/v1.0/reports/UserRegistrationDetails
```

运行调用后，您会收到类似于以下文本的错误响应：

```
'error': {
    'code': 'Authentication\_RequestFromNonPremiumTenantOrB2CTenant',
    'message': 'Neither tenant is B2C or tenant doesn't have premium license',
    'innerError': {
        'date': '2021-03-04T07:53:51',
        'request-id': 'a0a074e6-xxx-c511669fa420',
        'client-request-id': 'a0a074e6-xxx-c511669fa420'
    }
}
```

## 解决方案

### 方案 1：查询用户登录活动

1. 确保目标租户具有 Entra ID Premium P1 或 P2 许可证。 在 Azure 门户中，转到 **Microsoft Entra ID**，选择 **“概述”**，然后检查 **“许可证** ”值。 有关详细信息，请参阅 [注册 Microsoft Entra ID P1 或 P2 版本](/zh-cn/entra/fundamentals/get-started-premium)。
2. 验证是否已向 Microsoft Graph 访问令牌授予 `AuditLog.Read.All` 和 `Directory.Read.All` 权限。

### 场景 2：查询凭证用户注册详情

1. 确保目标租户具有 Entra ID Premium P1 或 P2 许可证。
2. 验证是否已向 Microsoft Graph 访问令牌授予 `Reports.Read.All` 权限。
3. 验证应用程序的身份验证用户或服务主体是否处于以下必需的管理角色之一：
   - 报告读取者
   - 安全读取器
   - 安全管理员
   - 全球阅读器
   - 全局管理员

## 详细信息

如果仅使用 **AuditLog.Read.All** 权限配置应用程序，则可能会间歇性地发生此错误。 这是预期行为，因为需要 **Directory.Read.All** 权限来检索租户许可信息（如果尚未缓存）。 为避免此错误，请确保同时包含这两个权限。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/users-groups-entra-apis/b2c-or-tenant-premium-license-sign-in-activities)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
