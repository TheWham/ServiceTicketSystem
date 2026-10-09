# 错误AADSTS220501 - 无法下载证书吊销列表

## 概要

本文提供了使用基于证书的身份验证时发生的Microsoft Entra 身份验证错误AADSTS220501的解决方案。

## 现象

尝试使用基于证书的身份验证登录到应用程序时，会收到以下消息AADSTS220501错误：

> 无法下载证书吊销列表（CRL）。 来自 CRL 分发点 {source} 的响应无效或无响应

## 原因

证书吊销列表（CRL）不可访问或已过期。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 通过 Web 浏览器打开 CRL 分发点 URL，验证 CRL 文件路径是否可公开访问。

   下面是 CRL 分发点 URL 的示例：

   `http://Contoso.com/CRLfilepath/CRLfilename.crl`

   若要查找租户的 CRL 分发点 URL，请参阅 [使用 Microsoft Entra 管理中心](/zh-cn/entra/identity/authentication/how-to-certificate-based-authentication#configure-certification-authorities-using-the-microsoft-entra-admin-center)配置证书颁发机构。
2. 如果无法访问 CRL 文件路径，请将 CRL 移动到公开可用的位置。

   如果 CRL 文件路径可访问，请打开 CRL 文件，转到**“常规**”选项卡，然后在“下一次更新**”字段中检查**表示 CRL 到期日期的日期和时间。 如果此日期和时间早于当前系统日期，Windows 计算机将使针对此 CRL 检查的证书失效。 必须手动续订 CRL 并替换过期的 CRL。

## 详细信息

有关身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/azure/active-directory/develop/reference-error-codes)。

若要调查单个错误，请转到 `https://login.microsoftonline.com/error`。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-aadsts220501-unable-to-download-certificate-revocation-list)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
