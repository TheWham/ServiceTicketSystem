# 错误AADSTS7000110：请求不明确，找到多个应用程序标识符

## 概要

本文介绍如何解决 `AADSTS7000110` 应用程序尝试从 Microsoft Entra ID 获取或刷新令牌时发生的错误。

## 现象

尝试登录到可与 Microsoft Entra ID 一起使用的 Azure 应用程序时，会收到以下 `AADSTS7000110` 错误消息：

> 请求不明确，找到多个应用程序标识符。 用于获取授权的客户端 ID（例如刷新令牌或授权代码）可能与在此请求或客户端凭据中传递的客户端 ID 不匹配。

## 原因

应用程序尝试执行以下操作之一：

- 兑换 OAuth2 授权代码以获取具有错误应用程序 ID（`client_id` 参数）的访问令牌或刷新令牌。
- 使用最初颁发给其他调用方的应用程序 ID 的刷新令牌。

## 解决方案

使用 OAuth2 授权代码或来自同一应用程序 ID（`client_id` 参数）的刷新令牌。

## 详细信息

有关身份验证和授权错误代码的完整列表，请参阅 [Microsoft Entra 身份验证和授权错误代码](/zh-cn/entra/identity-platform/reference-error-codes)。

若要调查单个错误，请转到 <https://login.microsoftonline.com/error>。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/error-code-aadsts7000110-request-is-ambiguous)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
