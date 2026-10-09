# 启动或网络属性更改后，DNS 请求似乎是随机的

本文提供有关启动或网络属性更改后似乎是随机的 DNS 请求的一些信息。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 4564934

## 总结

你有一台运行 Windows 8 或更高版本的计算机，并且至少有一个配置如下的网络适配器：

- 适配器未连接到域网络
- 适配器未配置 WINS 服务器

计算机启动或网络属性更改后，你可能会发现计算机发出一两个看似随机的 DNS 名称解析请求。

## 原因

在某些情况下，Windows DNS 客户端可能会发送看似随机的 DNS 名称解析请求。 这些请求用于各种目的，例如检测网络条件。 此 Windows 请求行为可能会更改。

## 详细信息

Windows DNS 客户端发送查询时，无需执行任何操作。 阻止这些查询可能会影响 Windows 性能。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/dns-requests-random-network-properties-change)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
