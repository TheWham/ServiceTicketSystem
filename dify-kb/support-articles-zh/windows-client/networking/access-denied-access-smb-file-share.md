# 在 Windows 中访问 SMB 文件共享时出现"拒绝访问"

## 摘要

本文帮助你解决在 Windows 上访问服务器消息块（SMB）文件共享时出现的**拒绝访问**错误。文章提供分步指南，帮助你识别并修复常见原因，包括较新 Windows 版本中的安全变更和配置不匹配。这些解决方案可确保安全、无缝地访问共享文件夹，从而提高工作效率并减少排查时间。请先使用"[先确定原因](#identify-the-cause-first)"部分来确定合适的解决方案。

> **重要**
> 从 **Windows 11 版本 24H2** 和 **Windows Server 2025** 开始，多项 SMB 安全功能**默认强制执行**。如果"拒绝访问"是在**操作系统升级之后**开始出现，而共享以前可以正常工作，请先查看[按操作系统版本划分的行为变化](#行为变化按操作系统版本划分)。

## 症状

当你连接到 Windows 文件服务器、第三方设备或网络附加存储（NAS）设备上的共享文件夹时，可能出现以下一种或多种症状：

- `Access is denied.`（拒绝访问）或 `You do not have permission to access \\server\share.`（你没有权限访问 \\server\share）。
- `You can't access this shared folder because your organization's security policies block unauthenticated guest access.`（你无法访问此共享文件夹，因为你组织的安全策略阻止未经身份验证的来宾访问。）
- 映射失败并出现 `System error 5`（`net use`，系统错误 5），或出现 `0x80070035`（找不到网络路径）、`STATUS_ACCESS_DENIED (0xC0000022)` 等状态代码。
- 该连接在升级到 **Windows 11 版本 24H2** 或 **Windows Server 2025** 之前可以正常工作，升级后失败。

## 行为变化（按操作系统版本划分）

大多数现代的"拒绝访问"案例是由"默认安全"变更引起的，而非配置错误。请先检查这些变更。

| 变更 | 自以下版本起默认启用 | 适用时的症状 |
|---|---|---|
| **禁用不安全（未经身份验证的）来宾访问** | Windows 10 1709 / Windows 11（专业版、企业版、教育版）/ Windows Server | "…security policies block unauthenticated guest access"；SMBClient **事件 ID 31017** |
| **要求 SMB 签名（入站和出站）** | Windows 11 24H2 / Windows Server 2025 | 与不支持签名的设备的连接被拒绝 |
| **提供 SMB 客户端 NTLM 阻断；NTLM 受限** | Windows 11 24H2 | 访问 IP 地址、工作组或 NAS 目标（无法使用 Kerberos 的环境）时被拒绝访问 |
| **SMB 身份验证速率限制器** | Windows Server 2022+ | 重复的登录失败会被延迟（约 2 秒），可能表现为锁定或响应缓慢 |

## 先确定原因

在 SMB **客户端**上运行以下检查，以确定适用哪种情况：

```powershell
# 出现了什么错误？目标是什么？
net use
# 现有/尝试的 SMB 会话和方言
Get-SmbConnection
# 客户端安全状况（签名、来宾、NTLM、加密）
Get-SmbClientConfiguration
```

同时查看**事件查看器** > **应用程序和服务日志** > **Microsoft** > **Windows** > **SMBClient**（**Connectivity** 和 **Security** 通道）。事件 ID 和消息会直接指向本文所述的各个分支。

## 原因与解决方案

### 1. 未经身份验证的来宾访问被阻止（现代客户端上最常见）

**适用情形：** 消息中提到"unauthenticated guest access"，或 SMBClient 记录**事件 ID 31017**。服务器或 NAS 接受来宾访问，但 Windows 默认不再允许来宾登录。

**解决方案：** 使用**有效凭据**连接服务器或 NAS，而不是依赖来宾访问。**不要**把重新启用来宾登录作为修复手段，除非将其视为一种临时的、风险自担的变通方法，因为这会使客户端暴露于恶意服务器和中间人攻击。有关详情以及（不建议的）策略覆盖方法，请参阅[在 SMB2 和 SMB3 中启用不安全的来宾登录](/windows-server/storage/file-server/enable-insecure-guest-logons-smb2-and-smb3)。

### 2. 要求 SMB 签名但目标不支持

**适用情形：** 共享位于第三方服务器或 NAS 上，而客户端是默认要求签名的 **Windows 11 24H2 / Windows Server 2025**。

**解决方案：** 在服务器或 NAS 上启用 SMB 签名（首选）。如果设备无法支持签名，请在更改客户端要求之前评估安全影响。请参阅[控制 SMB 签名行为](/windows-server/storage/file-server/smb-signing#smb-signing-behavior)以及 [SMB 安全强化](/windows-server/storage/file-server/smb-security-hardening)中的概述。

### 3. NTLM 被阻止或不可用

**适用情形：** 在配置了 SMB NTLM 阻断的客户端上，通过 **IP 地址**、连接到**工作组**设备，或连接到无法使用 Kerberos 的 NAS。

**解决方案：** 使用服务器的 **Kerberos 可用名称**（FQDN）而非 IP 进行连接，确保名称解析和 SPN 配置正确，或为必需的旧目标配置 NTLM 例外列表。请参阅[阻止通过 SMB 进行 NTLM 身份验证](/windows-server/storage/file-server/smb-ntlm-blocking)。

### 4. 重复失败被 SMB 身份验证速率限制器限流

**适用情形：** 在 **Windows Server 2022+** 上多次登录失败后，出现间歇性的拒绝访问或身份验证缓慢。

**解决方案：** 解决底层的凭据错误或映射问题。仅当限制器确实干扰了合法的大批量场景时，才调整或禁用它。请参阅[配置 SMB 身份验证速率限制器](/windows-server/storage/file-server/configure-smb-authentication-rate-limiter)。

### 5. 共享或 NTFS 权限不匹配（包括基于访问的枚举）

**适用情形：** 特定用户或组被拒绝访问，而其他用户可以正常访问；或文件夹被隐藏。

**解决方案：** 验证**共享**权限和 NTFS（安全）权限**两者**都向用户授予了所需访问权限，并检查基于访问的枚举（Access-Based Enumeration）。请参阅[无法在 Windows 中通过文件资源管理器访问共享文件夹](/troubleshoot/windows-client/networking/cannot-access-shared-folder-file-explorer)。

### 6. 缺少 SYNCHRONIZE 访问控制项（NetApp Filer / NAS 边缘案例）

**适用情形：** 通过 SMB2 访问 **NetApp Filer** 或其他 SMB2 服务器上的文件夹时被拒绝访问，且网络抓包显示针对该文件夹的 SMB2 **CREATE** 请求出现 `DesiredAccess` 失败。目标文件夹缺少 **SYNCHRONIZE** 访问控制项（ACE）。

**解决方案：** 使用 `ICACLS` 授予包含 Synchronize 位的权限：

```console
ICACLS h:\folder /grant domain\user:(RC,RD,REA,RA,X,S)
```

括号中的权限分别为：`RC` 读取控制、`RD` 读取数据或列出目录、`REA` 读取扩展属性、`RA` 读取属性、`X` 执行或遍历、`S` 同步。

**验证：** 确认文件夹已设置 Synchronize 位。文件夹 ACL 中应列出 `SYNCHRONIZE`（例如通过 [AccessChk](/sysinternals/downloads/accesschk)）：

```console
accesschk.exe -ld <folder>
```

请参阅 [SMB2 客户端上 SYNCHRONIZE 位的行为](/openspecs/windows_protocols/ms-smb2/a64e55aa-1152-48e4-8206-edd96444e7f7)。

## 提交支持工单前收集数据

如果上述解决方案无法解决问题，请先收集以下数据，以便支持团队无需反复沟通即可对工单进行分类处理：

```powershell
# 客户端状况
Get-SmbClientConfiguration | Out-File C:\SMBdata\client-config.txt
Get-SmbConnection          | Out-File C:\SMBdata\connections.txt

# 在客户端和服务器上同时抓取网络跟踪，然后重现问题
netsh trace start capture=yes scenario=NetConnection tracefile=C:\SMBdata\smb.etl
# ... 重现"拒绝访问"问题 ...
netsh trace stop
```

同时导出涵盖问题重现时间窗口的 **SMBClient** 事件日志以及（服务器上的）**SMBServer** 事件日志。

## 相关内容

- [SMB 安全强化](/windows-server/storage/file-server/smb-security-hardening)
- [Windows 和 Windows Server 中的 SMB 功能](/windows-server/storage/file-server/smb-feature-descriptions)
- [控制 SMB 签名行为](/windows-server/storage/file-server/smb-signing)
- [在 SMB2 和 SMB3 中启用不安全的来宾登录](/windows-server/storage/file-server/enable-insecure-guest-logons-smb2-and-smb3)
- [阻止通过 SMB 进行 NTLM 身份验证](/windows-server/storage/file-server/smb-ntlm-blocking)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/access-denied-access-smb-file-share)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
