# 将 UAC 配置为“提示输入凭据”时，映射的驱动器无法通过提升的提示提供

本文提供了解决映射驱动器在提升的命令提示符下不可用的问题的方法。

*适用于：* Windows 7 Service Pack 1、Windows Server 2012 R2  
*原始 KB 数：* 3035277

## 现象

如果满足以下条件，则会出现此问题：

- 使用组策略首选项（GPP）或登录脚本在登录期间映射网络驱动器。
- 已启用用户帐户控制（UAC）。
- 以下 UAC 组策略设置配置为提示输入凭据：  
  **用户帐户控制：管理员审批模式下管理员提升提示的行为**
- 配置 `EnableLinkedConnections` 了注册表项。 [请参阅配置 EnableLinkedConnections 注册表项](#detail-to-configure-the-enablelinkedconnections-registry-entry)的详细信息。

在这些情况下，你将遇到以下情况：

- 登录到客户端时，映射的驱动器按预期提供。
- 以管理员身份运行提升的命令提示符时，映射的驱动器在提升的命令提示符中不可用。

注意

此问题还会影响在提升的上下文（以管理员身份运行）中运行的其他应用程序，并使用驱动器号访问映射的驱动器。

## 原因

启用 UAC 后，系统会在用户登录时创建两个登录会话。 这两个登录会话相互链接。 一个会话表示在提升的会话期间的用户，另一个会话在最低用户权限下运行。

创建驱动器映射时，系统将创建将驱动器号与 UNC 路径关联的符号链接对象（DosDevices）。 这些对象特定于登录会话，在登录会话之间不共享。

注意

注册表项 `EnableLinkedConnections` 强制将符号链接写入启用 UAC 时创建的两个链接登录会话。

将 UAC 策略配置为 **提示输入凭据**时，除了现有的两个链接登录会话之外，还会创建新的登录会话。 以前创建的表示驱动器映射的符号链接在新登录会话中不可用。

## 解决方法 - 方法 1

1. 在本地组策略编辑器中，找到以下组策略路径：  
   本地计算机策略\Windows 设置\安全设置\本地策略\安全选项
2. 将以下策略配置为 **提示同意**： **用户帐户控制：管理员审批模式下管理员提升提示的行为**

## 解决方法 - 方法 2

例如，使用.bat脚本文件，在提升的会话中再次映射所需的驱动器。

## 配置 EnableLinkedConnections 注册表项的详细信息

1. 在注册表编辑器中，找到并单击以下注册表子项：  
   `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System`
2. 右键单击**“配置**”，选择“新建**”**，然后选择**“DWORD”（32 位）值**。
3. 将新的注册表项命名为 *EnableLinkedConnections*。
4. 双击 **EnableLinkedConnections** 注册表项。
5. 在**“编辑 DWORD 值**”对话框中，在**“值数据**”字段中键入 *1*，然后选择“**确定**”。
6. 退出注册表编辑器，然后重启计算机。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/mapped-drives-not-available-from-elevated-command)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
