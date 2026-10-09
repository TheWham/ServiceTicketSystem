# 排查本地策略阻止的密码重置问题

本文可帮助你排查用户或管理员无法重置或更改密码的情况，因为本地 Active Directory密码策略禁止密码。

## 现象

在[Azure 门户](https://portal.azure.com)中，执行以下步骤：

1. 选择“Microsoft Entra ID”>“用户”。
2. 从列表中选择用户。
3. **选择“重置密码**”链接。
4. 输入用户要使用的临时密码。
5. 选择“重置密码”按钮。

在这种情况下，会收到以下错误消息：

> 很遗憾，无法重置此用户的密码，因为本地策略不允许此操作。 请查看本地策略以确保其设置正确。

## 原因

错误消息由本地域控制器发送。 若要获取有关该问题的详细信息，请执行以下步骤。

注意

此过程要求为帐户管理 - 失败**事件启用域控制器的审核策略**。 有关详细信息，请参阅 [审核帐户管理](/zh-cn/windows/security/threat-protection/auditing/basic-audit-account-management)。

1. 转到本地域控制器。
2. 打开事件查看器管理单元。 为此，请选择“开始”，输入 *eventvwr.msc*，然后按 Enter。
3. 在**边栏中的事件查看器（本地）**节点下，展开 **Windows 日志**，然后选择“**安全性**”。
4. 查找包含**事件 ID 4724**、**审核失败**（在**关键字**列）和**用户帐户管理**（在任务类别**列中）的**审核事件。 这些事件应类似于以下示例：

   ```
   Log Name:      Security
   Source:        Microsoft-Windows-Security-Auditing
   Date:          11/5/2020 2:44:01 AM
   Event ID:      4724
   Task Category: User Account Management
   Level:         Information
   Keywords:      Audit Failure
   User:          N/A
   Computer:      ADDS01.Contoso.net
   Description:
   An attempt was made to reset an account's password.

   Subject:
       Security ID:        Contoso\MSOL_73c8a9aa6173
       Account Name:       MSOL_73c8a9aa6173
       Account Domain:     Contoso
       Logon ID:           0xF91C5C

   Target Account:
      Security ID:        Contoso\User01
      Account Name:       User01
      Account Domain:     Contoso

   Event Xml:
   <Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
     <System>
       ...
     </System>
   </Event>
   ```

此示例确认密码写回按预期工作。 但是，输入的密码不符合本地 Active Directory 密码策略。 由于密码长度、复杂性、年龄或其他要求，可能会违反策略。

## 解决方案

提供满足本地 Active Directory 密码策略的密码。

首先，验证密码策略的当前设置，以确定任何冲突。 然后，转到域控制器，并使用以下一个或多个方法：

- 从本地域控制器打开管理命令提示符窗口，并运行 [net accounts](../../../windows-server/networking/net-commands-on-operating-systems) 命令：

  ```
  C:\>net accounts

  Force user logoff how long after time expires?:       Never
  Minimum password age (days):                          0
  Maximum password age (days):                          42
  Minimum password length:                              7
  Length of password history maintained:                24
  Lockout threshold:                                    Never
  Lockout duration (minutes):                           30
  Lockout observation window (minutes):                 30
  Computer role:                                        PRIMARY
  The command completed successfully.
  ```
- 或者，打开管理 PowerShell 窗口，然后运行 [Get-ADDefaultDomainPasswordPolicy](/zh-cn/powershell/module/activedirectory/get-addefaultdomainpasswordpolicy) cmdlet：

  ```
  PS C:\WINDOWS\system32> Get-ADDefaultDomainPasswordPolicy

  ComplexityEnabled           : True
  DistinguishedName           : DC=contoso,DC=net
  LockoutDuration             : 00:30:00
  LockoutObservationWindow    : 00:30:00
  LockoutThreshold            : 0
  MaxPasswordAge              : 42:00:00
  MinPasswordAge              : 00:00:00
  MinPasswordLength           : 7
  objectClass                 : {domainDNS}
  objectGuid                  : 01234567-89ab-cdef-0123-456789abcdef
  PasswordHistoryCount        : 24
  ReversibleEncryptionEnabled : False
  ```
- 在管理命令提示符窗口中，。 在浏览器窗口中打开导出的报表（*GPreport.htm*），然后在“帐户策略/密码策略**”下**查看策略设置。

  ![组策略 H T M L 报告的屏幕截图。请参阅“设置”、“策略”、“Windows 设置”、“安全设置”、“帐户策略/密码策略”中的设置。](media/password-writeback-not-compliant-on-premises-ad-pwd-policy/group-policy-report-browser-window.png)

是否使用 [精细密码策略配置了本地 Active Directory 密码策略](/zh-cn/windows-server/identity/ad-ds/get-started/adac/introduction-to-active-directory-administrative-center-enhancements--level-100-#fine_grained_pswd_policy_mgmt)？ 如果是，请通过运行 [net user](/zh-cn/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/cc771865(v=ws.11)) 命令（`net user <username> /domain`）：

```
C:\>net user User01 /domain

User name                    User01
Full Name                    User01
Comment
User's comment
Country/region code          000 (System Default)
Account active               Yes
Account expires              Never

Password last set            11/5/2020 1:57:43 PM
Password expires             12/17/2020 1:57:43 PM
Password changeable          11/5/2020 1:57:43 PM
Password required            Yes
User may change password     Yes

Workstations allowed         All
Logon script
User profile
Home directory
Last logon                   Never

Logon hours allowed          All

Local Group Memberships
Global Group memberships     *Domain Users
The command completed successfully.
```

输入的密码是否符合本地 Active Directory 密码策略，但问题仍然存在？ 如果是这样，请检查你是否在本地 AD DS 环境中使用 [Microsoft Entra Password Protection](/zh-cn/azure/active-directory/authentication/concept-password-ban-bad-on-premises) ，或者是否在域控制器上安装任何第三方密码筛选器软件。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/password-writeback-not-compliant-on-premises-ad-pwd-policy)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
