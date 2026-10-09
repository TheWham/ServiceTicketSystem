# 无法在 Microsoft Entra Connect 中启用设备写回选项

*原始产品版本：*云服务（Web 角色/辅助角色），Microsoft Entra ID、Office 365 标识管理、Microsoft Intune  
*原始 KB 数：* 3085068

## 概要

本文提供有关解决无法在 Microsoft Entra Connect 中启用 **设备写回** 选项的问题的指导。

## 现象

运行 Microsoft Entra Connect 配置向导时，无法在“自定义同步选项”页上启用**“设备写回**”选项。

## 原因

如果满足以下条件之一，则可能会出现此问题：

- 未为设备写回启用Microsoft Entra 组织。
- 环境中拥有操作主角色（也称为灵活单一主操作或 FSMO 角色）的一个或多个域控制器不会复制。

## 解决方法

### 步骤 1：排查 FSMO 角色或复制问题

1. `repadmin /showrepl`运行该命令以显示显示复制状态的报表。 为此，请按照下列步骤进行操作：

   1. 以管理员身份打开命令提示符。
   2. 运行下面的命令：

      ```
      repadmin /showrepl * /csv > replication.csv
      ```
   3. 检查Replication.csv文件，然后排查并更正任何错误。
2. 抓住 FSMO 角色。 在某些情况下，保留 FMSO 角色的服务器可能无法正确播发自身。 抓住自身可能会解决问题。 为此，请按照下列步骤进行操作：

   1. 在安装了远程服务器管理工具包的域控制器或计算机上，以管理员身份打开命令提示符。
   2. 运行下面的命令：

      ```
      netdom query FSMO
      ```
3. 对于输出中列出的每台计算机，请按照使用 Ntdsutil.exe 将 FSMO 角色传输到域控制器[的“抓住 FSMO 角色”部分中](https://support.microsoft.com/help/255504)的步骤进行操作。

### 步骤 2：为组织启用设备写回

在安装了 Microsoft Entra Connect 的服务器上执行以下步骤：

1. 确保已安装远程服务器管理工具包。 有关详细信息，请参阅 [安装或删除远程服务器管理工具包](https://technet.microsoft.com/library/cc730825.aspx)。
2. 以管理员身份打开适用于 Windows PowerShell 的 Active Directory 模块。 有关详细信息，请参阅 [使用 Windows PowerShell](https://technet.microsoft.com/library/dd378937%28v=ws.10%29.aspx) 的 Active Directory 管理。
3. 转到 `%ProgramFiles%\Microsoft Azure Active Directory Connect\AdPrep`，然后运行以下命令：

   ```
   Import-module .\AdSyncPrep.psm1
   ```

   ```
   Initialize-ADSyncDeviceWriteBack -domainname <domain.com>
   ```

   在此命令中，占位符 <domain.com> 表示 Active Directory 域。 例如，运行 `Initialize-ADSyncDeviceWriteBack -domainname contoso.com`。

   你可能必须针对 Active Directory 环境中的每个域运行此命令。
4. 出现提示时，输入企业管理员用户名。
5. 打开Microsoft Entra Connect 配置向导。 现在应该能够启用设备写回。

## 详细信息

在安装了 Microsoft Entra Connect 的服务器上，查看以下位置的日志：

`C:\Users\<UserAccount which AAD Connect was installed>\AppData\Local\AADConnect\trace-<DateTime>.log`

你可能会看到如下所示的错误消息：

> [13：15：30.864] [ 18] [ERROR] ADPowerShellQueyProvider：SearchAdSyncDirectoryObjects 未能运行 ldap 搜索查询。 传递给 PowerShell 的参数值：  
> ForestFqdn ： <Forest\_Name>  
> AdConnectorId ： <ID>  
> PropertiesToRetrieve ： msDS-DeviceLocation，name，displayName，distinguishedName，objectClass  
> NamingContextType ： 配置  
> BaseDnType ： Relative  
> AdConnectorUserName ： <Domain>\MSOL\_d95558f154ee  
> BaseDn ： CN=Services  
> LdapFilter ： （objectClass=msDS-DeviceRegistrationService）  
> SearchScope ： Subtree  
> 异常详细信息：  
> System.Management.Automation.CmdletInvocationException：从对 COM 组件的调用返回了 HRESULT E\_FAIL 错误。
> >--- System.Runtime.InteropServices.COMException：从对 COM 组件的调用返回了 HRESULT E\_FAIL 错误。 at mmsServerRCW.IMMSServer2.SearchADSyncDirectoryObjects（String forestFqdn， guid& adConnectorGuid， String namingContextType， String baseDnType， String baseDn， String ldapFilter， String searchScope， String propertiesToLoad， String userName， String password， String& outputSerializedResult） at Microsoft.IdentityManagement.PowerShell.Cmdlet.AdSyncDirectorySearchResult.ProcessRecord（）

还可以在遇到问题的域控制器上看到以下事件 2092 警告消息，事件查看器登录：

> 事件 ID：2092  
> 任务类别：Replicaiton  
> 级别: 警告  
> 说明:  
> 此服务器是以下 FSMO 角色的所有者，但并不认为它有效。 对于包含 FSMO 的分区，自此服务器重启以来，此服务器未成功与任何合作伙伴复制。 复制错误阻止验证此角色。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/cannot-enable-device-writeback)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
