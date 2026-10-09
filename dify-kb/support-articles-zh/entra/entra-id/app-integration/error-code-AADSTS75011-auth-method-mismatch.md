# 错误 - AADSTS75011 用户在服务中用于身份验证的身份验证方法与请求的身份验证方法 AuthnContextClassRef 不匹配

## 概要

本文介绍在尝试登录到已与 Microsoft Entra ID 集成的基于 SAML 的单一登录（SSO）配置的应用时，收到错误消息“错误 - AADSTS75011身份验证方法，通过该方法对服务进行身份验证的用户与请求的身份验证方法 AuthnContextClassRef 不匹配”。

注意

本文有帮助吗? 你的输入对我们很重要。 请使用此页上的 **“反馈** ”按钮告诉我们本文为你工作得有多好，或者我们如何改进它。

## 现象

尝试使用基于 SAML 的 SSO 登录到已设置为使用 Microsoft Entra ID 进行标识管理的应用程序时， `AADSTS75011` 会收到错误消息。

## 原因

该 `RequestedAuthnContext` 请求位于 SAML 请求中。 这意味着应用需要 `AuthnContext` 指定的 `AuthnContextClassRef`。 但是，在访问应用程序之前，用户已经进行了身份验证，并且 `AuthnContext` 用于上述身份验证的（身份验证方法）不同于所请求的身份验证方法。 例如，发生了对 MyApps 和 WIA 的联合用户访问权限。
`AuthnContextClassRef`将是 `urn:federation:authentication:windows`。 Microsoft Entra ID 不会执行新的身份验证请求，它将使用 IdP（在本例中为 ADFS 或任何其他联合身份验证服务）传递的身份验证上下文。 因此，如果应用请求了其他 `urn:federation:authentication:windows`应用，则会出现不匹配的情况。 另一种情况是使用 MultiFactor： `'X509, MultiFactor`。

## 解决方法

`RequestedAuthnContext` 是一个可选值。 如果可能，请询问应用程序是否可以删除该值。

另一个选项是确保 `RequestedAuthnContext` 将遵循该值。 这是通过请求新的身份验证完成的。 通过执行此操作，处理 SAML 请求时，将完成新的身份验证并 `AuthnContext` 得到遵守。 若要请求全新身份验证，SAML 请求必须包含值。 `forceAuthn="true"`

## 详细信息

有关 Active Directory 身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/azure/active-directory/develop/reference-aadsts-error-codes)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-AADSTS75011-auth-method-mismatch)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
