# 尝试注册设备时出错：无法连接到服务

*原始产品版本：*Windows 8.1 企业版、Windows Server 2012 R2 Standard、Windows Server 2012 R2 Datacenter、Microsoft Entra ID  
*原始 KB 数：* 3045378

## 现象

尝试执行 Workplace Join 操作并从 Windows 8.1 设备将设备注册到本地 Active Directory 域时，将收到以下错误消息：

> 无法连接到服务  
> 目前无法连接到所需的服务。 请检查网络连接，或稍后重试。

## 原因

此问题可能由以下原因之一发生：

- 尽管 Active Directory 联合身份验证服务 （AD FS） 代理服务器可以解析联合服务器的名称，但该名称解析为错误的主机。
- AD FS 服务未在 AD FS 代理服务器上运行。
- 未安装 WAP 角色。
- 已安装 WAP 角色，但未配置。

## 解决方法

若要解决该问题，请执行以下步骤：

1. 登录到 AD FS 代理服务器：

   1. 运行服务管理控制台（services.msc）。
   2. 找到 AD FS 服务。
   3. 验证服务是否处于“已启动”状态。
2. 验证内部 AD FS 实例的名称解析：

   1. 在 AD FS 代理服务器中，打开命令提示符。
   2. 键入 `PING adfsserver.contoso.com`，然后按 Enter。

   注意

   占 `adfsserver.contoso.com` 位符表示 AD FS 服务器的地址，例如 `sts.contoso.com`。
3. 不要担心 PING 是成功还是失败。 相反，请注意目标地址是否解析为服务器的 IP 地址。
4. 如果地址不正确，请更正解决方法冲突：

   - 检查 AD FS 代理服务器上的 Hosts 文件，以查看是否包含正确的条目以及它是否面向 AD FS 实例。
   - 如果不使用 Hosts 文件，请使用 `Nslookup` 命令检查内部 DNS 以验证 DNS 记录。

## 详细信息

有关故障排除的详细信息，请参阅以下文章：

[排查工作区加入问题的诊断日志记录](https://support.microsoft.com/help/3045377)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/cant-connect-service-error-register-device)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
