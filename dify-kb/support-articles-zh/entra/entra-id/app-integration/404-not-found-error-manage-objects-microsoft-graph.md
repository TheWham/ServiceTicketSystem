# 使用 Microsoft Graph 管理对象时出现 404 错误

本文提供了 404（找不到对象）错误的解决方案，该错误是在尝试管理刚刚使用 Microsoft Graph 创建的 Microsoft Entra 对象时发生的。

## 现象

假设使用 Microsoft Graph 在 Microsoft Entra ID 中创建对象（例如用户、组或应用程序）。 尝试管理对象（例如在创建对象后不久获取、更新或修补对象）时，会收到 404（找不到对象）错误。

## 原因

[Microsoft Entra ID 体系结构](/zh-cn/entra/architecture/architecture)可确保所有数据在地理分布的数据中心之间复制。 出现此问题的原因是复制延迟跨所有数据中心传播新创建的对象。 此复制过程可能需要几分钟才能完成。

如下图所示，当应用程序通过 Microsoft Graph 发出请求以在 Microsoft Entra ID 中创建用户时，服务将开始复制过程并返回该用户的对象，其中包括用户的 ID 以及请求中使用的其他相关数据。 如果应用程序立即尝试更新此用户，它可能会连接到尚未使用新用户对象更新的副本。 因此，你会收到 404 错误，因为该副本上找不到用户。

![说明 404 错误原因的关系图。](media/404-not-found-error-manage-objects-microsoft-graph/404-not-found-error-diagram.png)

## 解决方案

若要解决此问题，请等待一段时间，然后重试更新请求。 如果重试后仍发生 404 错误，请加倍等待时间，然后重试。 通过允许足够的时间进行复制，可以阻止再次发生此错误。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/404-not-found-error-manage-objects-microsoft-graph)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
