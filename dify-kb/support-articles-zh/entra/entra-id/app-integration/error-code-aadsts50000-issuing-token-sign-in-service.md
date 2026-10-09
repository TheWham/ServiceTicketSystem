# AADSTS50000获取令牌或登录到 Azure 应用时出错

## 概要

使用令牌终结点的身份验证过程或令牌获取流期间，可能会出现AADSTS50000错误。 这些错误可能有多个原因。 本文提供了此错误的常见方案和解决方法。

## 症状

当用户尝试登录到集成到 Microsoft Entra ID 中的应用程序时，用户会收到以下错误消息：

> AADSTS50000：颁发令牌或登录服务时出错。

## 原因 1：用户密码已过期、无效或同步

此问题在混合环境中很常见。 用户的联合帐户密码在本地 Active Directory和Microsoft Entra ID 之间可能不同步。 此外，在撤销用户会话时，也可能发生此问题。

### 原因 1 的解决方案

重置用户密码，然后验证新密码是否可以成功进行身份验证以Microsoft Entra ID。

## 原因 2：令牌获取请求中未正确配置参数

此问题通常发生在代表 （OBO） 流中。 令牌获取所需的某些参数可能缺失或无效。

### 原因 2 的解决方案

请确保客户端 ID 有效，并正确配置其他必需参数。 有关详细信息，请参阅[Microsoft 标识平台和 OAuth 2.0 代理流](/zh-cn/entra/identity-platform/v2-oauth2-on-behalf-of-flow)。

## 原因 3：同意相关问题

此问题可能发生在 OAuth2 设备代码授予流中，流向令牌终结点。 用户登录到浏览器窗口并接受同意对话框后，将发生此错误。

### 原因 3 的解决方案：验证应用程序同意设置

1. 在[Azure 门户](https://portal.azure.com)中，确保租户的企业**应用程序**页上存在客户端应用程序（服务主体）。 可以按应用 ID 搜索应用程序。
2. 验证用户是否可以同意应用程序。 在“企业应用程序**”页上检查用户设置**，或查看影响用户同意的相关策略。

## 原因 4：应用程序或服务主体对象中使用对称签名密钥

Microsoft标识平台（v2 终结点）令牌必须由证书（非对称密钥）签名。 如果使用对称签名密钥，则可能会发生错误。

### 原因 4 的解决方案

#### 步骤 1：检查对称密钥是否在应用程序对象中使用

1. 在Azure 门户中，转到**应用注册**。
2. 在 **“管理** ”部分中，选择“ **清单**”。
3. 检查包含`keyCredentials`和 `type=Symmetric`. 的节中`usage=Sign`是否存在条目。

   [![显示应用程序清单密钥凭据代码的屏幕截图。](media/error-code-aadsts50000-issuing-token-sign-in-service/manifest-sample.png)](media/error-code-aadsts50000-issuing-token-sign-in-service/manifest-sample.png#lightbox)

或者，使用 Microsoft Graph PowerShell cmdlet [Get-MgApplication](/zh-cn/powershell/module/azuread/get-azureadapplicationkeycredential) 检索密钥凭据。

#### 步骤 2：检查是否在服务主体对象中使用对称密钥

1. 如果在Azure 门户的“应用注册**”页中**找不到应用程序，请浏览到“**企业应用程序**”页。
2. 找到应用程序，然后获取 **服务主体的对象 ID** 。
3. 使用 [Get-MgServicePrincipal](/zh-cn/powershell/module/microsoft.graph.applications/get-mgserviceprincipal) 检索密钥凭据。

#### 步骤 3：删除对称签名密钥

如果对称密钥存在：

- 使用 [Remove-MgApplicationKey](/zh-cn/powershell/module/microsoft.graph.applications/remove-mgapplicationkey) 删除应用注册的对称密钥。
- 使用 [Remove-MgServicePrincipalKey](/zh-cn/powershell/module/microsoft.graph.applications/remove-mgserviceprincipalkey) 删除服务主体对象的对称密钥。

如果需要签名密钥，请改用签名证书。 有关详细信息，请参阅 [基于 SAML 的单一登录：配置签名证书](/zh-cn/graph/application-saml-sso-configure-api?tabs=http%2Cpowershell-script#step-6-configure-a-signing-certificate)。

## 原因 5：资源应用程序中未公开委派权限（Web API）

在以下方案中可能会出现此错误：

- 你有一个在租户 A 中注册的多租户资源应用程序。此应用程序仅 **公开应用程序权限** 类型。
- 在租户 B 中，已注册客户端应用程序。 在此 **应用程序的 API 权限** 页中，为租户 A 中注册的资源应用程序配置权限。
- 可以使用 OAuth 2 委托的授权流（例如身份验证代码授予流）为用作 `/.default` Web API 范围值的资源应用请求访问令牌。

### 原因 5 的解决方案

配置资源应用程序以公开委派的权限，然后同意客户端应用程序中的该委派权限。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-aadsts50000-issuing-token-sign-in-service)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
