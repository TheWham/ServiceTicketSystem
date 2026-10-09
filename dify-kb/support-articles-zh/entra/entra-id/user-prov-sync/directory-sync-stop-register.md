# 目录同步到Microsoft Entra ID 停止，或者你警告同步在一天内未注册

## 概要

本文介绍 Azure Active Directory 同步工具中的性能问题。 该工具停止同步，或报告同步未在 24 小时内运行。

*原始产品版本：*Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2882421

注意

本文有帮助吗? 你的输入对我们很重要。 请使用此页上的 **“反馈** ”按钮告诉我们本文为你工作得有多好，或者我们如何改进它。

## 现象

你遇到以下症状之一：

- Azure Active Directory 同步工具Microsoft停止同步。
- 你会收到电子邮件，指出Microsoft Entra ID 在过去 24 小时内未注册同步尝试。
- 在该工具中 `MIISClient.exe` ，你会收到“Stopped-Server-Down”消息或“Stopped-Extension-DLL-Exception”消息。
- 无法启动一个或多个目录同步服务。

注意

默认情况下，目录同步每隔三个小时运行一次。

## 原因

如果出现下述一个或多个情况，则可能发生此问题：

- 在配置向导中用来设置目录同步的工作或学校帐户出现下述某个问题：

  - 帐户已删除。
  - 帐户已禁用。
  - 帐户密码已过期。
- 一个或多个目录同步服务的登录帐户出现下述某个问题：

  - 帐户已删除。
  - 帐户已禁用。
  - 帐户密码已过期。

  注意

  会自动配置目录同步服务的登录帐户，不应对其进行修改。
- 用于目录同步的管理员帐户已更改。
- 存在网络连接问题。
- 目录同步服务已停止。

## 解决方法

### 方法 1：手动验证服务是否已启动，以及管理员帐户是否可以登录

1. 选择“开始”，选择**“运行**”**，键入 **Services.msc**，然后选择“**确定**”。**
2. 找到Microsoft Entra Synchronization 设备服务，然后检查服务是否已启动。 如果未启动该服务，请右键单击该服务，然后选择“ **启动**”。

   - 如果使用 Azure Active Directory 同步工具，请查找 **Azure Active Directory 同步服务**。
   - 如果使用 Microsoft Entra Connect，请查找 **azure AD Sync** Microsoft。
3. 验证用于目录同步的管理员帐户是否仍然存在。 并验证帐户是否允许登录。 如果该帐户仍然存在，请重置密码，然后验证是否可以登录。 如果系统提示，请更改密码。

   如果不知道用于配置目录同步的全局管理员帐户，请在安装了目录同步设备的服务器上执行以下步骤：

   1. 转到 `%ProgramFiles%\Microsoft Azure AD Sync\UIShell\`，然后运行 Miisclient.exe。

      注意

      如果使用 Microsoft Entra Connect 或 Azure Active Directory 同步服务，请选择“开始”**，然后搜索并打开**同步服务**。**
   2. 选择**连接器**，然后双击 Microsoft Entra 连接器。
   3. 选择“连接”。
   4. 记下 UserName 值。 它是用于配置目录同步的全局管理员帐户。
4. 在目录同步服务器上，运行 Microsoft Entra Synchronization 设备配置向导。 键入用于目录同步的管理员帐户的新密码，然后按照向导中的其余步骤操作。
5. 出现提示时，选中“ **强制目录同步** ”复选框。

### 方法 2：解决目录同步服务的登录帐户问题

1. 选择“开始”，选择**“运行**”**，键入 Services.msc，然后选择“**确定**”。**
2. 找到Microsoft Entra Synchronization 设备服务：

   - 如果使用 Azure Active Directory 同步工具，请查找 **Azure Active Directory 同步服务**。
   - 如果使用 Microsoft Entra Connect，请查找 **azure AD Sync** Microsoft。右键单击该服务，然后选择“ **属性**”。 在 **“登录** ”选项卡上，记下列出的帐户名称。

   注意

   不支持将任何目录同步服务配置为以本地系统帐户登录，并可能导致问题。
3. 在安装了管理工具的域控制器或计算机上，打开Active Directory 用户和计算机（Dsa.msc），右键单击域名，然后选择“**查找**”。 键入在步骤 2 中记下的帐户的名称，然后选择“ **立即**查找”。

   - 如果找到该帐户，请转到步骤 4。
   - 如果找不到该帐户，则可能已被删除。 有关如何还原此帐户的详细信息，请参阅 [Active Directory 回收站分步指南](/zh-cn/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/dd392261(v=ws.10))。 如果无法还原帐户，则必须卸载并重新安装目录同步客户端。
4. 右键单击该帐户，然后选择“ **属性**”。 在 **“帐户** ”选项卡上的“帐户”选项下 **，** 执行以下步骤：

   1. 确保 **选中“密码永不过期** ”复选框。
   2. 确保 **清除“帐户已禁用** ”复选框。 然后，执行以下操作之一：
   - **如果选中了“帐户”**复选框，请清除它以启用该帐户。 然后，重启Microsoft Entra Synchronization 设备服务。 为此，请选择“开始”，选择**“**运行**”，键入 Services.msc，然后选择“**确定**”。** 找到该服务，右键单击该服务，然后选择“ **重启**”。
     - 如果使用 Azure Active Directory 同步工具，请查找 **Azure Active Directory 同步服务**。
     - 如果使用 Microsoft Entra Connect，请查找 **azure AD Sync** Microsoft。
   - **如果已清除“帐户”**复选框，请转到步骤 5。
5. **如果已清除“帐户”**复选框，则可能手动更改了帐户的密码。 若要设置新密码，请打开Active Directory 用户和计算机，找到并右键单击该帐户，然后选择“**重置密码**”以重置密码。 记下设置的密码，因为下一步中必须使用它。
6. 在目录同步服务的登录帐户上设置密码：

   1. 选择“开始”，选择**“运行**”**，键入 Services.msc，然后选择“**确定**”。**
   2. 根据所使用的客户端设置以下服务的密码。 为此，请右键单击相应的服务，选择“属性**”**，选择**“登录**”选项卡，然后键入密码。

      | Microsoft Entra Synchronization 客户端 | Microsoft Entra Connect |
      | --- | --- |
      | Forefront Identity Manager 同步服务  SQL Server （MOSONLINE） （如果存在）  Azure Active Directory 同步服务 | Azure AD Sync |
   3. 启动为其设置了新密码的服务或服务。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/directory-sync-stop-register)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
