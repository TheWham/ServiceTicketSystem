# Microsoft Entra Hybrid Sync Agent 安装问题 - 服务器上没有此类对象

本故障排除指南重点介绍对象引用未设置为对象实例时。 这种情况可能会阻止你安装 Microsoft Entra Connect 预配代理。

## 先决条件

若要安装 *云预配代理*，需要满足以下先决条件： [Microsoft Entra Connect 云同步](/zh-cn/azure/active-directory/cloud-sync/how-to-prerequisites)的先决条件。

## 方案 1

安装云预配代理时，可能会在安装过程中收到此错误。

> 创建组托管服务帐户时出错（gMSA）。 错误：服务器上没有此类对象。

安装向导的跟踪文件不清楚缺少的内容：

```
[15:16:14.583] [ 16] [ERROR] Exception creating gmsa. Exception: System.DirectoryServices.DirectoryServicesCOMException (0x80072030): There is no such object on the server.

   at System.DirectoryServices.DirectoryEntry.Bind(Boolean throwIfFail)
   at System.DirectoryServices.DirectoryEntry.Bind()
   at System.DirectoryServices.DirectoryEntry.get_NativeObject()
   at System.DirectoryServices.DirectoryEntry.InvokeGet(String propertyName)
   at Microsoft.Online.Deployment.Framework.Providers.GroupManagedServiceAccountProvider.CreateGroupManagedAccount(String serviceAccountName, String serviceDnsName, String username, String password)
[15:16:14.585] [ 16] [ERROR] Exception caught while creating gmsa. Exception: System.DirectoryServices.DirectoryServicesCOMException (0x80072030): There is no such object on the server.
```

若要解决此问题，请使用Active Directory 用户和计算机管理单元（*dsa.msc*）。 此管理单元在域控制器中验证托管服务帐户**容器是否存在**。

![Active Directory 用户和计算机窗口的屏幕截图。](media/azure-ad-hybrid-sync-no-such-object-on-server/2-active-directory-users-computers.png)

如果容器缺失，请联系 Windows Directory 服务团队，使用 `ADPrep /Domainprep` 命令还原或创建容器。

以下项Active Directory 域[服务要求](/zh-cn/windows-server/security/group-managed-service-accounts/getting-started-with-group-managed-service-accounts)：

> 要创建 gMSA，gMSA 域的林中的 Active Directory 架构需要更新到 Windows Server 2012。
>
> 可以通过安装运行 Windows Server 2012 的域控制器或从运行 Windows Server 2012 的计算机运行adprep.exe*版本*来更新架构。 对象的 `CN=Schema,CN=Configuration,DC=< name of DC >,DC=Com` 对象版本属性值必须为 52。

## 方案 2

在与上述类似的方案中，可能会收到以下错误：

> 创建组托管服务帐户时出错（gMSA）。 错误：服务器上没有此类对象。

向导跟踪显示以下信息：

```
[01:12:13.924] [  9] [INFO ] IsServiceAccountGMSA:: Checking if service account is gmsa
[01:12:13.924] [  9] [INFO ] Get current service credentials.
[01:12:13.938] [  9] [INFO ] IsServiceAccountGMSA:: Service account: NT SERVICE\AADConnectProvisioningAgent is not gmsa.
[01:12:15.414] [  9] [INFO ] IsServiceAccountGMSA:: Checking if service account is gmsa
[01:12:15.414] [  9] [INFO ] Get current service credentials.
[01:12:15.418] [  9] [INFO ] IsServiceAccountGMSA:: Service account: NT SERVICE\AADConnectProvisioningAgent is not gmsa.
[01:12:15.468] [  9] [ERROR] Exception creating gmsa. Exception: System.DirectoryServices.DirectoryServicesCOMException (0x80072030): There is no such object on the server.

   at System.DirectoryServices.DirectoryEntry.Bind(Boolean throwIfFail)
   at System.DirectoryServices.DirectoryEntry.Bind()
   at System.DirectoryServices.DirectoryEntry.get_NativeObject()
   at System.DirectoryServices.DirectoryEntry.InvokeGet(String propertyName)
   at Microsoft.Online.Deployment.Framework.Providers.GroupManagedServiceAccountProvider.CreateGroupManagedAccount(String serviceAccountName, String serviceDnsName, String username, String password)
[01:12:15.472] [  9] [ERROR] Exception caught while creating gmsa. Exception: System.DirectoryServices.DirectoryServicesCOMException (0x80072030): There is no such object on the server.
```

验证并确认域中存在托管服务帐户容器后，客户端轻型目录访问协议 （LDAP） 跟踪会显示以下信息：

```
9638 [2]0144.1380::04/14/21-14:17:20.2063638 [Microsoft_Windows_LDAP_Client/Debug16 ] Message=ldap_search called for connection 0x4392e0d8: DN is <WKGUID=1eb93889e40c45df9f0c64d23bbb6237,DC=*****,DC=com>. SearchScope is 0x0. AttributesOnly is 0x0. 

9679 [1]0144.1380::04/14/21-14:17:20.2075574 [Microsoft_Windows_LDAP_Client/Debug16 ] Message=4e 61 6d 65 45 72 72 3a 20 44 53 49 44 2d 30 33  NameErr:.DSID-03
9680 [1]0144.1380::04/14/21-14:17:20.2076087 [Microsoft_Windows_LDAP_Client/Debug16 ] Message=31 30 30 32 33 38 2c 20 70 72 6f 62 6c 65 6d 20  100238,.problem.
9681 [1]0144.1380::04/14/21-14:17:20.2076151 [Microsoft_Windows_LDAP_Client/Debug16 ] Message=32 30 30 31 20 28 4e 4f 5f 4f 42 4a 45 43 54 29  2001.(NO_OBJECT)
```

代理找不到托管服务帐户 （MSA） 容器的 WellKnown 全局唯一标识符（GUID）。

可以使用以下 PowerShell 命令验证此错误：

```
$ListOWKO = Get-ADObject (Get-ADRootDSE).DefaultNamingContext -Properties otherwellKnownObjects

$ListOWKO.otherwellKnownObjects
```

上一命令的输出显示以下结果：

```
B:32:1EB93889E40C45DF9F0C64D23BBB6237:CN=Managed Service Accounts\0ADEL:8b637607-65e8-4a80-b194-f738b26b9414,CN=Deleted Objects,DC=< name of DC >,DC=com
```

[![Active Directory 命令的输出的屏幕截图。输出显示其他已知对象中的缺失属性。](media/azure-ad-hybrid-sync-no-such-object-on-server/4-powershell-output-for-attribute.png)](media/azure-ad-hybrid-sync-no-such-object-on-server/4-powershell-output-for-attribute.png#lightbox)

此孤立元数据值指示以下方案之一：

- MSA 容器以前已被删除，但未正确还原。
- 值缺失。

OtherWellKnownObjects **属性的**默认值为：

> B：32：1EB93889E40C45DF9F0C64D23BBB6237：CN=托管服务帐户，DC=< DC >名称，**DC=com**

若要解决此问题，请与 Windows Directory 服务团队开具票证。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/azure-ad-hybrid-sync-no-such-object-on-server)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
