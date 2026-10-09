# 无法使用设备注册服务执行工作区加入

本文介绍用户无法使用设备注册服务将设备加入 Workplace 的问题。 它提供两个解决方法。

*原始产品版本：*Windows 8.1 企业版、Windows Server 2012 R2 Datacenter、Windows Server 2012 R2 Standard、Microsoft Entra ID  
*原始 KB 数：* 3045387

## 现象

当用户尝试使用设备注册服务执行 Workplace Join 时，用户会收到以下消息之一：

- 在提供用户的用户名和密码之前*，用户会收到以下消息*：

  > 确认你使用的是当前登录信息，并且工作区使用此功能。 此外，与工作场所的连接现在可能不起作用。 请稍候，然后重试。
- 用户在提供用户的用户名和密码后*收到以下消息*：

  > 无法连接到服务。

## 解决方法

若要解决上述任一问题，请使用适合这种情况的方法。

### 方法 1

若要修复消息 1 的问题，请查看正在尝试执行 Workplace Join 的客户端计算机上的事件日志以确定正确的解决方案。

管理员可能会在类似于以下示例的事件查看器中看到详细信息：

| 事件 ID： | （请参阅下表了解事件 ID。 |
| --- | --- |
| 日志名称: | Windows 7：应用程序和服务日志/Microsoft-Workplace-Join/Admin  Windows 8 或 Windows 10：应用程序和服务日志/Microsoft-Windows-Workplace-Join/Admin |
| 源： | Microsoft-Windows-Workplace 加入 |
| 级别: | 错误 |
| 说明: | （有关事件 ID 说明，请参阅下表。 |

| 事件 ID | 说明 | 解决方法 |
| --- | --- | --- |
| 103 | 工作区加入发现失败。 服务器返回了 http 状态 404。 | KB [3045386](https://support.microsoft.com/help/3045386) |
| 103 | 工作区加入发现失败。 服务器返回了 http 状态 503。 | KB 3045388 |
| 102 | 工作区加入发现失败。  退出代码：0x80072EE7。  无法解析服务器名称或地址。 无法连接到 `'https://EnterpriseRegistration.domainTEST.com:443/EnrollmentServer/contract?api-version=1.0'`。 | KB [3045385](https://support.microsoft.com/help/3045385) |
| 102 | 工作区加入发现失败。  退出代码：0x80072F19。  无法连接到吊销服务器或无法获取最终响应。 无法连接到 `'https://EnterpriseRegistration.domain.com:443/EnrollmentServer/contract?api-version=1.0'`。 | KB 3045384 |
| 102 | 工作区加入发现失败。  退出代码：0x80072F8A。  提供的证书已被吊销。 无法连接到 `'https://EnterpriseRegistration.domain.com:443/EnrollmentServer/contract?api-version=1.0'`。 | KB 3045383 |
| 102 | 工作区加入发现失败。  退出代码：0x80072F0D。  证书颁发机构无效或不正确。 无法连接到 `'https://EnterpriseRegistration.domain.com:443/EnrollmentServer/contract?api-version=1.0'`。 | KB 3045382 |
| 102 | 工作区加入发现失败。  退出代码：0x80072EFD。  无法建立与服务器的连接。 无法连接到 `'https://EnterpriseRegistration.domain.com:443/EnrollmentServer/contract?api-version=1.0'`。 | KB 3045381 |
| 102 | 工作区加入发现失败。  退出代码：0x80004005。  发生了未知错误。 无法连接到 `'https://EnterpriseRegistration.domain.com:443/EnrollmentServer/contract?api-version=1.0'`。 | KB 3045380 |
| 200 | “已达到用户可加入工作区的最大设备数。 | KB [3045379](https://support.microsoft.com/help/3045379) |

### 方法 2

若要修复消息 2 的问题，请在尝试注册设备[时看到](https://support.microsoft.com/help/3045378)“无法连接到服务”错误。

## 更多信息

若要快速排查这些问题，请尝试以下一项或多项操作。

### 验证 DNS

使用 `NSlookup`验证 DNS 配置，并验证答案是否正确。 为此，请打开命令提示符窗口，然后运行以下命令：

```
Nslookup enterpriseregistration.domain.com
```

- 如果使用 Microsoft Entra 联接：
  - 应返回作为目标的 CNAME 结果 `EnterpriseRegistration.windows.net` 。
- 如果使用 Windows Server Workplace Join：
  - 内部主机应返回内部 ADFS 节点。
  - 外部主机应返回外部 ADFS 代理地址。

### 刷新 DNS 缓存

以管理员身份打开命令提示符窗口，然后运行以下命令：

```
ipconfig /FlushDNS
```

### 验证是否已启用设备注册

如果尝试执行 Workplace Join 以Microsoft Entra ID：

1. 以公司管理员身份登录到Azure 门户，或从 Microsoft 365 管理中心 启动 Microsoft Entra ID 控制台。
2. 转到用户尝试执行加入的目录。
3. 转到 **“配置**”。
4. 向下滚动到 **“设备注册** ”部分。
5. 确保标记为 **“ENABLE WORKPLACE JOIN** ”的设置已切换为 **“是**”。 （“是”将是蓝色的。

如果尝试执行 Workplace Join 到本地 Active Directory 域，请执行以下操作：

- 打开Active Directory 联合身份验证服务（AD FS）管理控制台。
- 选择 **“信赖方信任** ”以确定是否在 AD FS 场的每个节点上启用设备注册服务信任。

### 验证Active Directory 联合身份验证服务服务和设备注册服务是否正在运行

如果尝试将工作区加入到本地 Active Directory，则应登录到 AD FS 场的每个节点，然后执行以下步骤：

1. 转到**“控制面板**、**管理工具**”和**“服务**”（Services.msc）。
2. 找到Active Directory 联合身份验证服务服务，并验证其状态。
3. 找到设备注册服务服务，并验证其状态。
4. 如果任一服务未运行，请启动服务。

### 验证是否已为 AD FS 场中的每个节点注册主机名绑定

如果尝试将工作区加入到本地 Active Directory，请按照以下 Microsoft TechNet 网站中的步骤操作：

[为网站配置主机标头 （IIS 7）](/zh-cn/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/cc753195(v=ws.10)?redirectedfrom=MSDN)

确保主机名（如 EnterpriseRegistration）。 domain\_name。 domain\_extension） 绑定到端口 443。

### 更新根证书

运行[Windows 更新](https://support.microsoft.com/windows/3c5ae7fc-9fb6-9af1-1984-b5e0412c556a)，并确保[已安装根证书](https://support.microsoft.com/help/931125)的更新

### 如果使用的是第三方代理或防火墙服务器，请验证是否启用了流量

如果尝试将工作区加入到本地 Active Directory，请验证是否有规则可启用到 EnterpriseRegistration 的传入 TCP 连接。
domain\_name。
domain\_extension。 它应允许流量传递到 DRS 服务器。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/dir-dmns-obj/cant-perform-workplace-join)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
