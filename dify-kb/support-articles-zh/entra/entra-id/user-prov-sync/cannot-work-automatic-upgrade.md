# Microsoft自动升级后 Entra Connect 无法正常工作

## 概要

本文讨论Microsoft Entra Connect 仅部分升级或密码同步以及密码写回功能被禁用的问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 4038479

## 现象

运行 Microsoft Entra Connect 1.1.443.0 或更低版本时，可能会遇到以下问题之一：

- Microsoft Entra Connect 仅部分升级，计划程序将暂停，并且不会发生自动同步周期。
- Microsoft Entra Connect 已正确升级，启用计划程序，并将对象更改正确同步到Microsoft Entra ID。 但是，密码同步功能或密码写回功能处于禁用状态。

## 原因

Microsoft Entra Connect 的自动升级功能出现问题，导致 **Microsoft.Azure.ActiveDirectory.Synchronization.Upgrader.exe** 进程因未经处理的异常而终止。 因此，自动升级不会完成。 若要验证，请执行以下步骤：

### 步骤 1：确定最近是否尝试升级 Microsoft Entra Connect 的自动升级

检查文件夹中的 `%ProgramData%\AADConnect` 日志文件。 具有标题的 `SyncEngine-AutoUpgrader-[Date]-[Time].log` 日志文件指示自动升级发生的时间。

![指示自动升级时间的日志文件的屏幕截图。](media/cannot-work-automatic-upgrade/log-file.png)

### 步骤 2：确定Microsoft Entra Connect 是否部分升级

运行 Microsoft Entra Connect 向导。 如果Microsoft Entra Connect 已部分升级，系统会提示升级Microsoft Entra Connect。

![Microsoft Entra Connect 向导的屏幕截图，其中提示升级Microsoft Entra Connect。](media/cannot-work-automatic-upgrade/upgrade-aad-connect.png)

### 步骤 3：将已安装的 Microsoft Entra Connect 版本与服务器配置中的版本进行比较

在自动升级期间，升级Microsoft Entra Connect 的当前安装，然后更新服务器配置中的版本。 如果两个版本不匹配，Microsoft Entra Connect 仅部分升级。

若要检查安装了哪个版本的 Microsoft Entra Connect，请在 控制面板 中打开**“程序和功能**”项，并检查 Microsoft Entra Connect 的版本号。

若要在服务器配置中检查 Microsoft Entra Connect 的版本，请在 Windows PowerShell 中运行以下命令，并查找 Microsoft.Synchronize.ServerConfigurationVersion **属性的值**：

```
(Get-ADSyncGlobalSettings).Parameters | select Name,Value
```

![屏幕截图显示了服务器配置中的 Microsoft Entra Connection 版本。](media/cannot-work-automatic-upgrade/serverconfigurationversion-property.png)

运行以下命令检查计划程序的状态：

```
Get-ADSyncScheduler
```

如果 SchedulerSuspended **的值**为 **True**，则计划程序将暂停。

![屏幕截图显示了 Microsoft Entra Connect 的计划程序状态。](media/cannot-work-automatic-upgrade/schedulersuspended-value.png)

### 步骤 4：验证是否已启用密码同步和密码写回

如果Microsoft Entra Connect 已正确升级，请打开Microsoft Entra Connect 向导，然后选择“ **查看解决方案** ”以验证是否启用了密码同步和密码写回功能。

## 解决方法

若要解决此问题，请执行以下步骤：

1. 启动Microsoft Entra Connect 向导，然后选择“ **升级**”。
2. 升级完成后，验证已安装的 Microsoft Entra Connect 版本是否与服务器配置中的版本匹配。
3. 如果以前启用了密码同步功能或密码写回功能，请验证升级完成后是否仍启用该功能。
4. 如果在升级后禁用了任何功能，请在 Microsoft Entra Connect 向导中选择“ **自定义同步选项** ”，然后手动启用该功能。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/user-prov-sync/cannot-work-automatic-upgrade)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
