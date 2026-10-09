# 使用扫描程序进行扫描可能会导致 TWAIN 感知应用程序挂起

本文提供了使用扫描程序扫描可能导致 TWAIN 感知应用程序挂起的问题的解决方法。

*适用于：* Windows 7 Service Pack 1  
*原始 KB 数：* 982436

来源：Microsoft 支持部门

## 快速发布

快速发布文章直接从 Microsoft 支持组织内提供信息。 本文中包含的信息是针对新兴或独特的主题创建的，或旨在补充其他知识库信息。

## 现象

当 32 位 TWAIN 感知应用程序在 64 位 Windows Vista 或 Windows 7 系统上使用 WIA 驱动程序扫描时，TWAIN 应用程序可能会停止响应。

## 原因

如果在推送 [扫描] 按钮之前将扫描对话框保持打开状态约 10 分钟，则用于将扫描图像从 WIA 驱动程序传输到 TWAIN 应用程序的消息不会发送到 TWAIN 应用程序。

## 解决方法

可以通过执行以下操作之一来避免此问题：

- 在打开扫描对话框后不久扫描图像。
- 使用 WIA 感知应用程序，而不是 TWAIN 感知应用程序。

## 详细信息

此行为是特意这样设计的。

## 免责声明

Microsoft和/或其供应商不作任何陈述或保证，说明此网站上发布的文档和相关图形（“材料”）中包含的信息的适用性、可靠性或准确性。 这些材料可能包括技术不准确或版式错误，随时可以不通知地进行修订。

在适用法律允许的最大范围内，Microsoft和/或其供应商否认，并排除所有表示、默示或法定条件，包括包括但不限于陈述、担保或标题条件、不侵权、满意条件或质量、适销性和针对特定目的的适用性。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/scanning-twain-aware-application-hang)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
