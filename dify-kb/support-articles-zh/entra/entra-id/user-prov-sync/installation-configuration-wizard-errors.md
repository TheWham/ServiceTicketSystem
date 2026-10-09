# 排查 Azure Active Directory 同步工具安装和配置向导错误

## 概要

本文介绍如何排查 Azure Active Directory 同步工具安装和目录同步工具配置向导问题。

*原始产品版本：*Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2684395

## 简介

本文提供了安装或设置目录同步工具时可能出现的错误消息的解决方法和常见原因。

## 查看系统要求

如果满足以下所有条件，则可以在计算机上安装 Azure Active Directory 同步工具：

- 计算机上安装 Windows PowerShell 1.0。
- 你以本地管理员组的成员身份登录到计算机。
- 计算机具有 64 位处理器。
- 计算机正在运行以下操作系统之一：
  - Windows Server 2003 x64 Service Pack 2（SP2）或更高版本
  - 基于 x64 的 Windows Server 2008 版本
- 计算机不是域控制器。
- 计算机已加入 Active Directory 域。 它位于要与 Microsoft Entra ID 同步的林中。
- 计算机上安装了 Microsoft .NET Framework 3.5 或更高版本。

## 检查权限

若要成功启动目录同步工具配置向导，登录到安装目录同步工具的计算机的用户必须是安装该工具期间添加的本地Microsoft标识集成服务器（MIIS）管理员组的成员。

运行目录同步工具配置向导时，必须提供以下信息：

- 本地 Active Directory架构的企业管理员凭据
- Microsoft云服务的全局管理员凭据

## 使用 nltest 检查域连接

[Nltest](/zh-cn/previous-versions/windows/it-pro/windows-server-2012-R2-and-2012/cc731935(v=ws.11)) 是内置于 Windows Server 中的命令行工具。 它作为适用于 Windows 10 [的远程服务器管理工具的](https://www.microsoft.com/download/details.aspx?id=45520)一部分提供。

- 若要检查域的域控制器，请在命令提示符处运行以下命令：

  ```
  nltest /dsgetdc:<FQDN of the domain>
  ```

  注意

  该工具 `nltest` 需要安装 Windows Server 2003 支持工具。

  如果设置正确，输出类似于以下示例：

  ```
  DC: \DC.contoso.com 
  Address:\ <IP Address> 
  Dom Guid: <GUID> 
  Dom Name: contoso.com 
  Forest Name: contoso.com 
  DC Site Name: Default-First-Site-Name 
  Our Site Name: Default-First-Site-Name 
  Flags: PDC GC DS LDAP KDC TIMESERV GTIMESERV WRITABLE DNS_DC DNS_DOMAIN DNS_FOREST CLOSE_SITE 
  The command completed successfully
  ```
- 若要检查计算机的站点成员身份，请在命令提示符处运行以下命令：

  ```
  nltest /dsgetsite
  ```

  成功的结果类似于以下示例：

  ```
  Default-First-Site-Name 
  The command completed successfully
  ```

## 错误 1：计算机必须加入域

若要解决此问题，请按照以下步骤检查计算机的域成员身份：

1. 登录到计算机。
2. 右键单击“ **我的计算机**”，然后选择“ **属性**”。
3. **选择“计算机名称**”选项卡。如果计算机是域成员，则**完整计算机名称**类似于 *ComputerName.Domain.xxx*。 域名显示在域**旁边**。

如果计算机是域成员，但仍会收到错误消息，请验证：

- 计算机可以与域通信。
- 计算机可以发现域控制器。

为此，请按照以下步骤操作：

1. `ipconfig`使用命令行工具检查服务器上的域名系统（DNS）设置。
2. 确认可以 ping 问题计算机上的网络属性中列出的 DNS 服务器。
3. `nslookup`运行命令行工具。 如果 DNS 服务器无法访问，则会收到错误消息。 例如，你会收到类似于以下示例的错误消息：

   > DNS 请求超时。  
   > 超时为 2 秒。  
   > 找不到地址 <IP 地址>的服务器名称：超时  
   > 默认服务器：UnKnown  
   > 地址： <IP 地址>

有时，将计算机加入工作组，然后将计算机加入域可能会解决此错误消息。 如果计算机无法加入域，则表示以下问题之一：

- 计算机在联系域控制器时遇到问题。
- Active Directory 域正在拒绝请求。

## 错误 2：已安装 Azure Active Directory 同步工具

在这种情况下，由于以前的挂起安装，可能无法安装目录同步工具。 安装包还会在安装过程中在后台安装软件。 若要解决此问题，请执行以下步骤：

1. 在控制面板中，检查Microsoft标识集成服务器是否列在**“添加或删除程序**”或“程序和功能**”中**。 如果存在，则必须将其删除。
2. 验证 Program Files 文件夹是否包含名为 *Microsoft Identity Integration Server* 的子文件夹。 如果子文件夹存在，则必须将文件夹重命名为 *Microsoft标识集成Server\_Old*。
3. 重新运行安装程序。

## 其他错误消息的疑难解答

可以在事件查看器查看所有目录同步日志记录。 若要查看与目录同步相关的所有事件，请执行以下步骤：

1. 打开“事件查看器”。
2. 展开 **Windows 日志**，然后展开 **应用程序**。
3. 在 **“操作** ”窗格中，选择“ **筛选当前日志**”。
4. 在 **“事件源** ”框中，选中“ **目录同步** ”复选框。
5. 选择“确定”。 下表列出了错误名称、错误详细信息、错误源和帮助解决错误的步骤。

| 错误名称 | 详细信息 | Source | 解决方法 |
| --- | --- | --- | --- |
| AdminRequired | 安装目录同步需要本地管理员权限 | 事件查看器/错误提示 |  |
| DirSyncAlreadyInstalled | 已安装目录同步工具。 版本 {0} | 事件查看器 | 在尝试安装最新版本之前，请卸载所有早期版本的目录同步工具。 |
| DirSyncInstallKeyNotRemoved | Windows Installer 无法从 Azure Active Directory 同步 MSI 中删除卸载注册表项。 重试卸载或联系Microsoft联机支持部门。 | 事件查看器 | 手动删除注册表项以完成安装。 |
| DirSyncNotInstalledError | 此计算机上未检测到 Azure Active Directory 同步工具的完整安装。 请卸载此工具的任何版本，然后重新安装最新版本。 | 事件查看器 | 在尝试安装最新版本之前，请卸载所有早期版本的目录同步工具。 |
| ErrorReRunConfigWizard | 由于配置问题，无法启动同步。 若要解决此问题，请尝试运行配置向导。 如果继续看到此错误，请联系Microsoft联机支持部门。 | 事件查看器 | 运行目录同步工具配置向导。 |
| WindowsInstaller45Required | 安装需要Microsoft Windows Installer 4.5。 请安装 Microsoft Windows Installer 4.5，然后重试。 | 事件查看器 | 确保安装目录同步工具的服务器满足最低要求。 |
| ErrorClearRunHistory | 无法清除 MIIS 服务器上的运行历史记录。 返回的错误为“”。{0} 请联系 Microsoft Online 支持人员。 | 事件查看器 |  |
| ErrorNoStartConnection | 由于连接问题或域控制器无法由服务器联系，同步无法启动。 验证是否已连接到服务器，并且所有配置的域控制器都已连接到网络。 如果最近删除了域或命名上下文，请重新运行配置向导。 | 事件查看器 | 确认可从运行目录同步工具的服务器访问本地 Active Directory 域控制器。 |
| ErrorNoStartCredentials | 由于凭据问题，同步无法启动。 重新运行配置向导以更新同步的凭据。 | 事件查看器 | 运行目录同步工具配置向导并重新输入凭据。 此外，请确认凭据有权访问门户。 |
| ErrorNoStartNoDomainController | 同步无法启动，因为服务器无法联系域控制器。 验证域控制器是否已连接到网络。 | 事件查看器 | 确认可从运行目录同步工具的服务器访问本地 Active Directory 域控制器。 |
| ErrorStoppedConnectivity | 由于连接丢失，同步已停止。 还原到服务器的连接。 |  | 确认本地计算机可以访问 Internet。 让用户尝试 ping `provisioning.microsoftonline.com` 以验证计算机是否可以访问 Microsoft Entra 身份验证系统。 |
| ErrorStoppedDatabaseDiskFull | 同步已停止，因为同步服务器使用的 SQL Server 数据库已满。 在 SQL Server 数据库中创建一些空间。 | 事件查看器 | 释放用于保存目录同步 SQL 数据库的存储空间。 如果问题未解决，目录同步工具将无法成功运行，SQL 数据库可能会永久损坏。 |
| InstallNotAllowedOnDomainController | Microsoft联机服务共存不能安装在域控制器上。 | 事件查看器 | 目录同步工具只能安装在未加入域的计算机上。 |
| InstallPathLengthTooLong | 安装路径太长。 提供 116 个字符或更少的路径，然后重试。 | 事件查看器 | 如果使用自定义路径安装目录同步工具，则总路径必须包含少于 116 个字符。 |
| InsufficientDiskSpace | 磁盘空间不足 | 事件查看器 | 没有足够的空间在本地工作站上安装目录同步工具。 |
| InvalidPlatform | 必须在运行 Windows Server 2003 Service Pack 2 或更高版本的计算机上安装 Azure Active Directory 同步工具。 | 事件查看器 | 确保安装目录同步工具的服务器满足最低要求。 |
| InvalidUPNFormat | 用户主体名称（UPN）是登录名。 当用户输入不包含“@”字符的 Microsoft Online 凭据时，将显示此错误。 | 事件查看器 | 输入有效的凭据。 |
| ADCredsNotValid | 你提供的企业管理员凭据无效。 提供有效的凭据，然后重试。 | 事件查看器 | 安装向导无法验证用于安装该工具的用户帐户是否为企业管理员。 |
| MachineIsDomainJoinedUserIsNot | 计算机已加入域，但当前用户凭据对域没有访问权限。 | 事件查看器 | 在尝试安装目录同步工具之前，使用满足最低要求的帐户以域用户身份登录。 |
| MachineIsNotDomainJoined | 计算机未加入任何域。 | 事件查看器 | 确保安装目录同步工具的服务器满足最低要求。 |
| MachineNotDomainJoined | 必须将计算机加入到域中。 | 事件查看器 | 确保安装目录同步工具的服务器满足最低要求。 |
| MIISSyncIsInProgressError | 同步引擎正忙。 完成此同步会话后重试此操作。 | 事件查看器 | MIIS 正在完成现有操作。 只有在当前操作完成之后，才能完成任何新操作。 |
| MIISUserAddRight\_AccountNotFound | 找不到帐户名：“{0}' 。 错误代码：{1} | 事件查看器 | 目录同步工具无法添加用于完成安装到 MIIS 管理员组的本地帐户。 手动将用户添加到组以继续安装。 |
| MIISUserAddRight\_AddFailed | {0}“”无法添加到“”{1}的帐户权限。 错误代码：{2} | 事件查看器 | 目录同步工具无法添加用于完成安装到 MIIS 管理员组的本地帐户。 手动将用户添加到组以继续安装。 |
| MIISUserAddRight\_PolicyHandleNotFound | 未能获取策略句柄。 错误代码：{0} | 事件查看器 | 目录同步工具无法添加用于完成安装到 MIIS 管理员组的本地帐户。 手动将用户添加到组以继续安装。 |
| PowerShellRequired | 必须安装 PowerShell。 | 事件查看器 | 确保安装目录同步工具的服务器满足最低要求。 |
| UnsupportedNameFormat | 不支持名称格式。 支持的用户名格式的两个示例为： `someone@example.com` 或 `example\someone`。 | 事件查看器 | 输入有效的凭据。 |
| UserNotAMemberOfMIISAdmins | 当前用户不是 Microsoft Identity Integration Server （MIIS） 管理组的成员。 如果最近安装了 Azure Active Directory 同步工具，可能需要注销，然后登录。 | 事件查看器 | 手动将用于运行目录同步工具的本地 Active Directory 用户帐户添加到 MIIS 管理员组。 |
| UserNotAnEnterpriseAdmin | 用户“”{0}不是企业管理员组的成员。 | 事件查看器 | 手动将用于运行目录同步工具的本地 Active Directory 用户帐户添加到 Active Directory 企业管理员组。 |
| UnsupportedClientVersion | 不再支持此版本的目录同步工具。 删除此版本，然后从 Microsoft Online Services 管理中心的“迁移”选项卡的“目录同步”页安装最新版本。 | 事件查看器 | 下载最新版本的目录同步工具。 为此，请转到 [安装或升级目录同步工具](/zh-cn/azure/active-directory/hybrid/how-to-dirsync-upgrade-get-started)。 |
| InternetQueryOptionError | 未读取 Internet Explorer 代理设置。 使用安装向导的初始配置可能无法访问联机帮助。 WinInet 错误 {0} | 事件查看器 | 安装向导无法在 Internet Explorer 中读取或更改代理设置。 验证 Internet Explorer 中设置的代理设置的格式是否正确。 |
| InternetSetOptionError | 未设置 Internet Explorer 代理设置。 使用安装向导的初始配置可能无法访问联机帮助。 WinInet 错误 {0} | 事件查看器 | 安装向导无法在 Internet Explorer 中读取或更改代理设置。 验证 Internet Explorer 中设置的代理设置的格式是否正确。 |
| RichCoexistenceNotAllowed | 当前本地目录未安装 Exchange 2010。 不允许丰富共存。 | 事件查看器 | 在尝试安装目录同步工具之前，请先安装混合部署的所有先决条件。 |

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/installation-configuration-wizard-errors)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
