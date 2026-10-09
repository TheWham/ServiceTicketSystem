# AADSTS500011 - 找不到资源主体

## 概要

本文介绍用户在尝试登录 Microsoft Entra ID 时遇到“AADSTS500011”错误的问题。

## 症状

当用户尝试登录到使用 Microsoft Entra ID 身份验证的应用程序时，他们会收到以下错误消息：

> `AADSTS500011 - The resource principal named [resource URL] was not found in the tenant named [tenant ID]`

## 原因

如果在租户中找不到资源主体（应用程序或服务），则会出现此问题。 如果出现以下情况，则会出现此问题：

- 租户中的管理员未预配资源应用程序。
- 租户中的任何用户都不同意资源应用程序。
- 未正确配置资源 URL。
- 租户 ID 不正确。

## 解决方案

若要解决此问题，请按照下列步骤操作：

1. **验证资源应用程序预配**：

   - 确保在Microsoft Entra ID 租户中正确注册应用程序（资源主体）。
   - 转到[Azure 门户](https://portal.azure.com)，导航到Microsoft Entra ID > Enterprise 应用程序。
   - 检查应用程序是否已列出并正确配置。
2. **同意应用程序**：

   - 确保资源应用程序已由租户中的管理员或用户同意。
   - 转到[Azure 门户](https://portal.azure.com)，导航到Microsoft Entra > Enterprise 应用程序。
   - 找到应用程序，并确保它具有必要的权限和同意。
3. **检查资源 URL**：

   - 验证错误消息中显示的资源 URL 是否与你在租户 ID 中预配的资源应用程序匹配。
   - 确保使用正确的资源 URL 发送身份验证请求。
4. **检查租户 ID**：

   - 验证错误消息中显示的租户 ID 是否与租户 ID 相同。
   - 确保身份验证请求发送到正确的Microsoft Entra ID 租户。

## 详细信息

有关身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/azure/active-directory/develop/reference-error-codes)。

若要调查单个错误，请转到 <https://login.microsoftonline.com/error>。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-aadsts500011-resource-principal-not-found)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
