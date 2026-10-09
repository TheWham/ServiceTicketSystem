# 错误AADSTS650056：配置错误的应用程序

## 概要

本文提供了“AADSTS650056：配置错误的应用程序”错误的故障排除步骤和解决方案。

## 现象

尝试登录到使用 Microsoft Entra ID 的 Web 应用程序时，会收到以下错误消息：

> AADSTS650056：配置错误的应用程序。 这可能是由于以下原因之一：客户端未在客户端的应用程序注册中请求的权限中列出“AAD Graph”的任何权限。 或者，管理员未在租户中表示同意。 或者，检查请求中的应用程序标识符，以确保它与所配置的客户端应用程序标识符匹配。 请联系你的管理员来修复配置或者代表租户来表示同意。

## 原因

此错误通常因以下原因之一而发生：

- SAMLRequest 中提供的颁发者无效。
- 应用程序没有调用 Microsoft Graph API 所需的权限。
- 管理员尚未代表租户同意该应用程序的权限。

## 解决方案 1：SAMLRequest 中提供的颁发者无效（对于 SAML 身份验证流）

在以下 SAML 请求示例中，颁发者值必须与企业应用程序中配置的标识符（实体 ID）匹配。 此值也称为 *标识符 URI* 或 *应用 ID URI*。 例如，SAML 请求可能类似于以下请求：

```
<samlp:AuthnRequest xmlns="urn:oasis:names:tc:SAML:2.0:metadata" ID="id6c1c178c166d486687be4aaf5e482730" Version="2.0" IssueInstant="2013-03-18T03:28:54.1839884Z" xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"> <Issuer xmlns="urn:oasis:names:tc:SAML:2.0:assertion">https://www.contoso.com</Issuer> </samlp:AuthnRequest>
```

在此示例中，标识符 URI 为 `https://www.contoso.com`。

若要修复不匹配，请执行以下其中一项操作：

- 更新企业应用程序中的标识符，使其与 SAML 请求中的颁发者匹配。
- 更新供应商端的 SaaS 应用程序配置，以便传递正确的发行方。

## 解决方案 2：验证应用程序权限和同意

如果组织拥有应用程序，请执行以下步骤：

1. 登录到 [Azure 门户](https://portal.azure.com)，转到 **“应用注册** ”屏幕，选择应用注册，然后选择 **API 权限**。
2. 确保应用程序至少具有**来自 Microsoft Graph** 的 **User.Read** 委托权限。
3. 选中 **“状态** ”字段以确定是否同意权限。 例如：

   - 如果权限未经许可，则该值显示为 **“挂起** ”或“空白”。
   - 如果权限已成功获得许可，则该值显示为“为 [租户名称]授予”。

   许可权限的示例：

   ![添加图形 API 权限的屏幕截图。](media/error-code-aadsts650056-misconfigured-app/graph-api-permissions.png)

如果组织不是应用程序所有者，请执行以下步骤：

1. 使用全局管理员帐户登录到应用程序。 应会看到一个同意屏幕，提示你授予权限。 在进行下一步之前，请确保您选择了**代表组织同意的选项**。

   同意屏幕示例：

   ![同意屏幕的屏幕截图](media/error-code-aadsts650056-misconfigured-app/consent-permissions.png)
2. 如果未看到同意屏幕，请从“ **企业应用程序** ”部分删除Microsoft Entra ID 中的应用程序，然后重试登录。

如果错误仍然存在，请转到下一个解决方案。

## 解决方案 3：手动生成同意 URL

如果应用程序旨在访问特定资源，则可能无法在 Azure 门户中使用 **“同意** ”按钮。 相反，可能需要手动生成同意 URL，然后打开 URL 以向应用程序授予权限。

### 针对授权 V1 接口

同意 URL 类似于以下文本：

```
https://login.microsoftonline.com/{Tenant-Id}/oauth2/authorize?response\_type=code
&client\_id={App-Id}
&resource={App-Uri-Id}
&scope=openid
&prompt=consent
```

例如：

```
https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/authorize
?response\_type=code
&client\_id=00001111-aaaa-2222-bbbb-3333cccc4444
&resource=https://vault.azure.net/
&scope=openid
&prompt=consent
```

### 关于授权 V2 API 终端点

同意 URL 类似于以下文本：

```
https://login.microsoftonline.com/{Tenant-Id}/oauth2/v2.0/authorize
?response_type=code
&client_id={App-Id}
&scope=openid+{App-Uri-Id}/{Scope-Name}
&prompt=consent
```

例如：

```
https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/v2.0/authorize
?response_type=code
&client_id=00001111-aaaa-2222-bbbb-3333cccc4444
&scope=openid+https://vault.azure.net/user_impersonation
&prompt=consent
```

- 如果应用程序以资源身份访问自身，**{App-Id}** 和 **{App-Uri-Id}** 是相同的。
- 可以从应用程序所有者获取 **{App-Id}** 和 **{App-Uri-Id}** 值。
- **{Tenant-Id}** 对应于你的租户标识符。 此值可以是域或目录 ID。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-AADSTS650056-misconfigured-app)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
