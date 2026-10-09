# NET USE 命令出现系统错误 85

本文可帮助修复非管理用户尝试重新连接到用户已使用该 `net use` 命令使用的共享网络驱动器时发生的系统错误 85。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 253821

## 现象

当非管理用户尝试重新连接到用户已使用的共享网络驱动器时，可能会生成系统错误 85（已在使用的本地设备名称）。

例如，在登录脚本中或命令提示符中运行以下命令序列说明了问题：

```
net use r: /d
net use r: \\servername\share
net use r: /d
net use r: \\servername\share
```

对于具有管理权限的用户，不会发生此行为。

## 原因

此行为是由以下注册表值中的 1 **设置**引起的：  
`HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\SessionManager\ProtectionMode`

如果设置为 **1**，则会发生此问题。 如果将设置更改为 **0** 并重新启动服务器，则问题将消失。

注意

建议将此值更改为 1 以限制对基本系统对象的更改，并解决符号链接的问题。

## 解决方法

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 但是，注册表修改不当可能会出现严重问题。 因此，按以下步骤操作时请务必谨慎。 作为额外保护措施，请在修改注册表之前先将其备份。 如果之后出现问题，您就可以还原注册表。 有关如何备份和还原注册表的详细信息，请参阅：[如何备份和还原 Windows 中的注册表](https://support.microsoft.com/help/322756)。

将条目 `HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\SessionManager\ProtectionMode` 从 **1** 更改为 **0**。

注意

如果运行的是基于 Windows Server 2003 的终端服务器，请将该值`ProtectionMode`**设置为 1**。 错误 85 转换为以下内容：  
ERROR\_ALREADY\_ASSIGNED本地设备名称已在使用中。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/system-error-85-net-use-command)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
