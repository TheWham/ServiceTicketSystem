# 错误AADSTS900439 - USGClient在公共端点不受支持

## 概要

本文提供了解决错误 AADSTS900439（USGClientNotSupportedOnPublicEndpoint）的方法，该错误会在尝试使用公有云终结点登录在 Azure 政府云中注册的应用程序时发生。

## 症状

尝试使用公共终结点登录到在 Azure 政府云中注册的应用程序时，登录会失败，并且收到AADSTS900439（USGClientNotSupportedOnPublicEndpoint）错误。

## 原因

Microsoft Entra 在 Azure 政府版中的管理门户已从 `https://login-us.microsoftonline.com` 更新为 `https://login.microsoftonline.us`。 此更改也适用于 Microsoft 365 GCC High 和 Microsoft 365 DoD 环境，Microsoft Entra 权限同样为 Azure 政府云提供服务。 Microsoft Entra ID 确保用于登录操作的正确终结点。 不能再使用公共终结点 `https://login-us.microsoftonline.com`登录到在 Azure 政府云中注册的应用程序。

有关详细信息，请参阅 [Microsoft Entra Authority 的 Azure 政府终端更新](https://devblogs.microsoft.com/azuregov/azure-government-aad-authority-endpoint-update)。

## 解决方案

若要解决此问题，请确保使用正确的 Azure 政府终结点执行登录操作。 下面是 Azure 服务和 Azure 政府终结点之间的映射：

| Name | Azure 政府端点 |
| --- | --- |
| Portal | `https://portal.azure.us` |
| Microsoft图形 API | `https://graph.microsoft.us` |
| Active Directory 终结点和授权 | `https://login.microsoftonline.us` |

有关详细信息，请参阅 [Azure 政府终结点映射](/zh-cn/azure/azure-government/documentation-government-developer-guide#endpoint-mapping)。

## 详细信息

每个国家/地区云环境都不同于全球Microsoft环境。 为这些环境开发应用程序时，请务必了解主要差异。 例如，注册应用程序、获取令牌和调用Microsoft图形 API 可能有所不同。

有关在国家云中注册应用程序的详细信息，请参阅 [应用注册终结点](/zh-cn/entra/identity-platform/authentication-national-cloud#app-registration-endpoints)。

有关在国家/地区云中获取令牌的详细信息，请参阅 [Microsoft Entra 身份验证终结点](/zh-cn/entra/identity-platform/authentication-national-cloud#azure-ad-authentication-endpoints)。

有关不同Microsoft Graph 国家云部署以及每个云中开发人员可用的功能的详细信息，请参阅 [Microsoft Graph 国家/地区云部署](/zh-cn/graph/deployments)。 下面是一个示例实现： [配置 .NET 应用程序以调用国家云租户中的 Microsoft Graph](https://blogs.aaddevsup.xyz/2020/06/configure-net-application-to-call-microsoft-graph-in-a-national-cloud-tenant)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-aadsts900439-usgclientnotsupportedonpublicendpoint)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
