# 无法使用 Azure Active Directory 同步工具同步 SystemMailbox 或 DiscoveryMailboxSearch 帐户

## 概要

本文提供有关解决尝试使用 Azure Active Directory 同步工具同步 SystemMailbox 和 DiscoverySearchMailbox 用户帐户时收到错误的问题的信息。

*原始产品版本：* 云服务（Web 角色/辅助角色）、Microsoft Entra ID、Microsoft Intune、Azure 备份、Office 365 标识管理  
*原始 KB 数：* 2804688

## 现象

使用 Microsoft Azure Active Directory 同步工具同步以下用户帐户时，会收到目录同步错误：

- SystemMailbox{1f05a927-beed-480c-b962-da8d1d7e16a8}@<DomainNameName>
- SystemMailbox{e0dc1c29-89c3-4034-b678-e6c29d823ed9}@<DomainName>
- DiscoverySearchMailbox{D919BA05-46A6-415f-80AD-7E093334BB852}@<DomainNameName>

## 原因

如果 Microsoft Exchange Server 2010 安装期间创建的三个用户帐户缺少属性数据，则会出现此问题。 在这种情况下，Azure Active Directory 同步工具使用属性数据来筛选掉这些用户帐户，并阻止它们同步到云。

## 解决方法

若要解决此问题，请根据需要使用以下方法之一。

### 方法 1

在安装了Active Directory 域服务管理工具的域控制器或计算机上，请执行以下步骤：

1. 打开 Active Directory 用户和计算机。
2. 在 **“视图** ”菜单上，选择“ **高级功能**”。
3. **选择“用户**”容器。
4. 双击每个 **SystemMailbox** 用户帐户，然后针对每个帐户执行以下步骤：

   1. 选择 **属性编辑器**。
   2. **查找 mailNickName** 属性，然后使用邮件**属性中包含的**值填充属性。
   3. 选择“确定”。
5. 双击每个 **DiscoverySearchMailbox** 用户帐户，然后针对每个帐户执行以下步骤：

   1. 选择 **属性编辑器**。
   2. **查找 mailNickName** 属性，然后使用邮件**属性中包含的**值填充属性。
   3. **找到 msExchRecipientTypeDetails** 属性，然后将属性的值设置为536870912。
   4. 选择“确定”。

#### 方法 2

在安装目录同步工具的计算机上，执行以下步骤：

1. 打开权限提升的命令提示符。
2. 打开 Windows PowerShell，键入 `Import-Module DirSync` ，然后按 Enter。
3. Windows PowerShell 会话启动后，运行以下 cmdlet：

   ```
   Start-OnlineCoexistenceSync
   ```

如果方法不起作用，请参阅 [“重新创建缺少仲裁邮箱](/zh-cn/exchange/architecture/mailbox-servers/recreate-arbitration-mailboxes#re-create-an-arbitration-mailbox)”。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/unable-sync-system-discovery-mailbox)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
