# SAML 身份验证中AADSTS76021“客户端发送的请求未签名”错误

## 概要

在使用基于 SAML 的单一登录（SSO）进行联合身份验证时，会发生 **AADSTS76021**（ApplicationRequiresSignedRequests）错误，该错误与 Microsoft Entra ID 相关。 此错误表示客户端未对请求进行签名，但应用程序需要签名的请求。 即使客户端对请求进行签名，也可能不会根据 SAML 绑定配置添加签名。

根据 [SAML 规范](https://docs.oasis-open.org/security/saml/v2.0/saml-bindings-2.0-os.pdf)，两种主要和最常用的绑定类型包括：

- **HTTP-Redirect** [urn：oasis：names：tc：SAML：2.0：bindings：HTTP-Redirect]：对于 HTTP get 方法（GET）请求，签名作为查询参数包含在 URL 中。
- **HTTP-POST** [urn：oasis：names：tc：SAML：2.0：bindings：HTTP-POST]：对于 HTTP POST 请求，签名嵌入 SAML 消息的 XML 有效负载中。

如果应用程序需要一个位置的签名，但请求使用另一个绑定类型，Microsoft Entra ID 会拒绝该请求。 此拒绝会导致 **AADSTS76021** 错误。

## 决议

1. **验证 SAML 绑定类型**

检查应用程序是否需要 HTTP-Redirect 或 HTTP-POST。

2. **验证配置匹配项**

验证标识提供者（IdP）和服务提供商（SP）配置是否一致。

3. **验证签名的位置**

- 对于 HTTP 重定向：签名必须位于查询字符串中。
- 对于 HTTP-POST：签名必须位于 XML `<Signature>` 元素内。

4. **更新应用程序或 IdP 配置**

- 对齐绑定类型和签名位置。
- 在Microsoft Entra ID 中，验证 **企业应用程序**>**单一登录**下的 SAML 设置。

## 例子

### 示例 1：HTTP-Redirect 绑定（GET）

签名的请求包括查询参数，如以下示例：

```
https://contoso.com?
SAMLRequest=<Base64EncodedRequest>&RelayState=<StateValue>&SigAlg=http://www.w3.org/2000/09/xmldsig#rsa-sha256&Signature=<Base64Signature>
```

### 示例 2：HTTP-POST 绑定（POST）

签名的请求在 XML 中包含签名，如以下示例所示：

```
<samlp:AuthnRequest>
    <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:SignedInfo>
            <!-- Canonicalization and signature details -->
        </ds:SignedInfo>
        <ds:SignatureValue>Base64SignatureValue</ds:SignatureValue>
        <ds:KeyInfo>
            <ds:X509Data>
                <ds:X509Certificate>...</ds:X509Certificate>
            </ds:X509Data>
        </ds:KeyInfo>
    </ds:Signature>
</samlp:AuthnRequest>
```

### SAML 2.0 绑定

SAML 2.0 定义了多个协议绑定，这些绑定将 SAML 请求和响应消息交换映射到标准通信协议。 这些绑定指定消息编码、签名放置和传输安全性的规则。

#### HTTP-Redirect 绑定

- **说明**：使用 HTTP GET 请求，其中 SAML 消息作为查询参数传输。
- **用例**：常见于启动身份验证请求。

#### HTTP-POST 绑定

- **说明**：使用 HTTP POST 请求，其中 SAML 消息作为 XML 嵌入在正文中。
- **用例**：常见于安全地发送已签名断言。

#### HTTP-Artifact 绑定

- **说明**：通过 HTTP 交换小型项目。 这些工件稍后解析为完整的 SAML 消息。
- **用例**：减少前端通信中的消息大小。

#### 简单对象访问协议 （SOAP） 绑定

- **说明**：使用 SOAP over HTTP 进行反向通道通信。
- **用例**：常用于构件解析和管理操作。

#### 反向 SOAP（PAOS）绑定

- **说明**：用于增强客户端或代理（ECP）配置文件的反向 HTTP 绑定。
- **用例**：启用高级客户端交互。

[SAML 绑定规范](https://docs.oasis-open.org/security/saml/v2.0/saml-bindings-2.0-os.pdf)

## 资源

有关 Active Directory 身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/azure/active-directory/develop/reference-aadsts-error-codes)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-aadsts76021-request-not-signed)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
