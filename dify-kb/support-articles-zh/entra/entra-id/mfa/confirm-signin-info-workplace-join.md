# 执行 Workplace Join 时出错：确认使用的是当前登录信息

本文介绍执行工作区加入操作时发生错误的问题。

*原始产品版本：*Windows 8.1 企业版、Windows Server 2012 R2 Datacenter、Windows Server 2012 R2 Standard、Microsoft Entra ID  
*原始 KB 数：* 3045386

## 现象

尝试执行工作区加入操作时，会收到以下错误消息：

> 确认你使用的是当前登录信息，并且工作区使用此功能。 此外，与工作场所的连接现在可能不起作用。 请稍候，然后重试。

此外，管理员可能会在事件查看器中看到以下事件详细信息：

> 事件 ID： 103  
> 日志名称：Microsoft-Windows-Workplace Join/Admin  
> 来源：Microsoft-Windows-Workplace Join  
> 级别：错误  
> 说明：工作区加入发现失败。 服务器返回了 http 状态 404。  
> `https://EnterpriseRegistration.domain.com:443/EnrollmentServer/contract?api-version=1.0`

## 原因

此问题是由下列原因之一导致的：

- 客户端将重定向到禁用或停止 DRS 终结点的内部设备注册服务（DRS）实例。
- EnterpriseRegistration 服务的 DNS 记录缺失或配置错误。
- 当前登录用户的域后缀未在 DRS 的 SSL 证书中考虑。
- 网络或防火墙正在阻止流量，或暂时性网络问题导致数据包丢失。

## 解决方法

### 验证 DNS

使用 `NSlookup` 该工具验证 DNS 配置，并验证答案是否正确。

为此，请打开命令提示符窗口，然后运行以下命令：

```
Nslookup enterpriseregistration.domain.com
```

- 如果使用 Microsoft Entra 联接
  - 这应返回作为目标的 CNAME 结果 `EnterpriseRegistration.windows.net` 。
- 如果使用 Windows Server Workplace Join
  - 内部主机应返回内部 AD FS 节点。
  - 外部主机应返回外部 AD FS 代理地址。

### 验证是否已启用设备注册

如果尝试执行 Workplace Join 以Microsoft Entra ID，请执行以下步骤：

1. 以公司管理员身份从 M365 管理中心登录到Azure 门户，或启动 Microsoft Entra ID 控制台。
2. 找到用户尝试加入操作的目录。
3. 转到“配置”。
4. 向下滚动到“设备注册”部分。
5. 确保标记为 ENABLE WORKPLACE JOIN 的设置已切换为“是”（是将为蓝色）。

如果尝试执行工作区加入到本地 Active Directory 域，请执行以下步骤：

1. 启动 AD FS 管理控制台，然后选择“信赖方信任”以确定是否在 AD FS 场的每个节点上启用设备注册服务信任。
2. 如果设备注册服务已启用，请检查服务控制台以确保设备注册服务已启动。

### 检查 SSLCertificate 绑定

如果尝试执行 Workplace Join 到本地 Active Directory 域，请执行以下步骤：

1. 以管理员身份打开命令提示符窗口，键入以下命令，并在每个命令后按 Enter 在 ADFS 代理或 ADFS 服务器上显示绑定：

   ```
   Netsh
   ```

   ```
   Http Show SSLCert
   ```
2. 确定是否存在 IP 端口绑定（而不是名称绑定）。
3. 如果 IP 端口绑定不存在，请查看以确定 EnterpriseRegistration 名称绑定是否存在。

## 详细信息

有关故障排除的详细信息，请参阅Microsoft知识库中的以下文章：

[排查工作区加入问题的](https://support.microsoft.com/help/3045377)诊断日志记录。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/confirm-signin-info-workplace-join)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
