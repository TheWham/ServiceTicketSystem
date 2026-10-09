# 排查在强制密码更改后首次登录后出现延迟的问题

本文介绍如何在用户被迫在首次登录时更改其密码时排查密码写回问题。

## 现象

用户在首次登录时进行所需的密码更改后，会收到以下警告消息：

> 密码已成功更新，但服务器需要一点时间才能赶上。 请在几分钟内再次尝试登录。

## 原因

当用户在首次登录时强制更改其密码Microsoft Entra ID 时，密码写回过程接受登录的临时密码，并提示用户提供新密码。 密码写回尝试更改本地密码，然后等待。 如果本地更新成功，密码写回会尝试更改 Microsoft Entra ID 中的密码。 在密码更改操作期间，密码写回会验证当前密码，然后提供在相应目录中更新的新密码。

但是，如果在重置本地 Active Directory密码后立即尝试登录，则计时问题可能会导致此警告。 如果用户在 **下次选择登录** 选项时必须更改密码，并且域身份验证配置为 **直通身份验证** （PTA），则会出现此问题。

在此方案中，用户在密码哈希同步完成将临时密码同步到 Microsoft Entra ID 之前尝试登录。 但由于配置了 PTA，身份验证将重定向到本地 Active Directory。 用户现在可以成功登录到 Microsoft Entra ID，然后被迫在第一次登录时更改密码。 如果密码更改成功，密码写回会更新本地 Active Directory和Microsoft Entra ID 中的新密码。 但是，登录消息显示“我们的服务器需要一点时间才能赶上”。这是因为临时密码与 Microsoft Entra ID 中的当前密码不匹配。

## 解决方案

Active Directory 管理员在本地重置密码后，Microsoft Entra Connect 至少需要两分钟才能将该临时密码同步到 Microsoft Entra ID。 为了避免收到此警告消息，用户必须等待至少两分钟才能登录并更新密码。 这为密码哈希同步提供同步临时密码的时间。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/password-writeback-servers-need-time-catch-up)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
