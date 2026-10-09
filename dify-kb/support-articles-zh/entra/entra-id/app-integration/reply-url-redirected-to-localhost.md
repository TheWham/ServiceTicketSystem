# Microsoft Entra ID 将令牌发送到错误的回复 URL 终结点或 localhost

## 概要

本文介绍Microsoft Entra ID 将令牌发送到不正确的回复 URL 终结点或 localhost 的问题。

## 现象

在单点登录期间，如果登录请求不包含显式回复 URL（断言使用者服务 URL），则 Microsoft Entra ID 会为该应用程序选择任意已配置的回复 URL。 即使应用程序配置了显式回复 URL，用户也可能重定向 `https://127.0.0.1:444`。

将应用程序添加为非库应用时，Microsoft Entra ID 将此回复 URL 创建为默认值。 此行为已更改，Microsoft Entra 默认情况下不再添加此 URL。

## 原因

未在 Microsoft Entra ID 中向用户授予访问应用程序的权限。

## 解决方法

删除为应用程序配置的未使用回复 URL。

在基于 SAML 的单一登录（SSO）配置页上，在 **“回复 URL”（断言使用者服务 URL）** 部分中，删除系统创建的未使用或默认回复 URL。 例如，`https://127.0.0.1:444/applications/default.aspx`。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/reply-url-redirected-to-localhost)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
