# 错误AADSTS50017 - 验证基于证书的身份验证的给定证书失败

## 概要

本文提供了使用基于证书的身份验证（CBA）访问应用程序或资源时出现的Microsoft Entra 身份验证AADSTS50017错误的解决方案。

## 症状

尝试使用 CBA 访问应用程序或资源时，登录过程会失败，并显示以下错误消息：

> AADSTS50017：验证基于证书的身份验证的给定证书失败。

## 原因 1：证书链失败或验证失败

由于以下问题，可能会出现AADSTS50017错误：

- 由于存储中缺少证书颁发机构 （CA） 证书，证书链失败。
- 使用者密钥标识符（SKI）和颁发机构密钥标识符（AKI）值的验证失败。

  在公钥基础结构（PKI）中，证书链验证过程可确保证书链的完整性和真实性。 SKI 和 AKI 在这个过程中扮演着关键角色。 SKI 为证书持有的公钥提供唯一标识符。 AKI 用于标识颁发证书的 CA。

若要解决此问题，请按照下列步骤操作：

1. 检查颁发证书是否已正确上传到受信任的证书列表。

   证书链由多个链接在一起的证书组成。 最终用户的证书可由根 CA 或非根 CA（中间 CA）颁发。 如果你有非根颁发 CA（中间 CA），则必须将中间证书和根 CA 证书上传到 Microsoft Entra CA 受信任存储。
2. 检查证书的 SKI 值，并确认 AKI 值是否与上传到受信任存储的任何中间或根 CA 证书匹配。

   如果没有匹配项，则应相应地更改证书或缺少的 CA 证书。 为此， [请使用 Microsoft Entra 管理中心](/zh-cn/entra/identity/authentication/how-to-certificate-based-authentication#configure-certificate-authorities-by-using-the-microsoft-entra-admin-center)配置证书颁发机构。

   若要获取 SKI 和 AKI 值，请检查证书的详细信息并上传颁发 CA 证书。

   [![显示证书链的屏幕截图。](media/error-code-aadsts50017-certificate-based-authentication-failed/certificate-chain-ski-aki-value.png)](media/error-code-aadsts50017-certificate-based-authentication-failed/certificate-chain-ski-aki-value.png#lightbox)

   | 证书类型 | 特征 |
   | --- | --- |
   | 根 CA 证书 | 它有自己的滑雪。 它可在适用时颁发中间证书。 它不包含 AKI 字段。 |
   | 颁发或中间 CA 证书（如果适用） | 其 AKI 指向根 CA 证书的 SKI。 它具有与用户证书上的 AKI 匹配的自己的 SKI。 它可以颁发用户证书，并在适用时颁发中间证书。 可以存在多个中间 CA 证书。 |
   | 最终用户（用户或客户端）证书 | 它有自己的滑雪。 其 AKI 指向颁发 CA 证书的 SKI。 |

## 原因 2：证书无效

如果证书链中的任何证书缺少有效的扩展标识符（例如证书策略扩展），则可能会发生AADSTS50017错误。

若要解决此错误，请验证证书链中所有证书的证书策略扩展，包括用户证书、中间 CA 证书和根 CA 证书。 确保证书策略扩展及其对象标识符（OID）在整个链中保持一致且有效。

若要验证策略 OID 的一致性和有效性，请检索链中的相关证书，并按如下所示对其进行验证：

[![显示证书策略的屏幕截图。](media/error-code-aadsts50017-certificate-based-authentication-failed/certificate-policies.png)](media/error-code-aadsts50017-certificate-based-authentication-failed/certificate-policies.png#lightbox)

如果任何证书缺少证书策略扩展，请使用嵌入的相应证书策略扩展重新颁发 CA 证书或最终用户证书。

有关策略扩展和其他受支持的扩展的详细信息，请参阅 [支持的扩展](/zh-cn/windows/win32/seccertenroll/supported-extensions)。

## AADSTS 错误代码参考

有关身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/entra/identity-platform/reference-error-codes)。 若要调查单个错误，请 `https://login.microsoftonline.com/error`搜索 。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-aadsts50017-certificate-based-authentication-failed)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
