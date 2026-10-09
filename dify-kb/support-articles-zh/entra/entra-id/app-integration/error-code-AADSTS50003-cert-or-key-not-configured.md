# 错误 AADSTS50003 - 没有配置签名密钥

## 概要

本文介绍在尝试登录到已与 Microsoft Entra ID 集成的基于 SAML 的单一登录（SSO）配置的应用时收到错误消息“错误AADSTS50003 - 未配置签名密钥”。

## 现象

尝试登录到已设置为使用基于 SAML 的 SSO 进行标识管理Microsoft Entra ID 的应用程序时收到错误 `AADSTS50003` 。

## 原因

应用程序对象已损坏，Microsoft Entra ID 无法识别为应用程序配置的证书。

## 解决方法

若要删除并创建新证书，请按照以下步骤操作：

1. 在基于 SAML 的 SSO 配置屏幕上，选择“SAML 签名证书”部分下的“**创建新证书”。**
2. 选择过期日期，然后单击“ **保存**”。
3. 勾选“使新证书处于活动状态”，以便覆盖活动证书。 然后，单击窗格顶部的“保存”并选择接受以激活滚动更新证书。
4. 在“SAML 签名证书”部分下，单击“删除”删除“未使用”的证书。

## 更多信息

有关 Active Directory 身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/azure/active-directory/develop/reference-aadsts-error-codes)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-AADSTS50003-cert-or-key-not-configured)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
