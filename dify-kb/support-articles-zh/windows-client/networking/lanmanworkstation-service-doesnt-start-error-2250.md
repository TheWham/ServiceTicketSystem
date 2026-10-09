# LanmanWorkstation 服务未启动时出现错误 2250 （NERR\_UseNotFound）

本文介绍如何解决 LanManWorkstation 服务未启动且 Windows 生成错误 2250 的问题。

*适用于：* Windows Server 2022、Windows Server 2019、Windows 11、Windows 10

## 现象

LanmanWorkstation 服务未启动，Windows 将生成以下消息：

> Windows 无法启动本地计算机上的工作站。 有关详细信息，请查看系统事件日志。 如果这是非Microsoft服务，请联系服务提供商，并参阅特定于服务的错误代码 2250。

注意

除了 LanmanWorkstation 服务之外，此行为可能会影响其他服务。

## 原因

此错误通常表示缺少以下易失性注册表项：

> 注册表子项： `HKLM\SYSTEM\CurrentControlSet\Control\ComputerName\ActiveComputerName`
>
> - 注册表类型：REG\_SZ
> - 注册表项：`ComputerName`
> - 值： <*Computer\_Name*>

此值应与以下非易失项的值相同：

> 注册表子项： `HKLM\SYSTEM\CurrentControlSet\Control\ComputerName\ComputerName`
>
> - 注册表类型：REG\_SZ
> - 注册表项：ComputerName
> - 值： <*Computer\_Name*>

注意

在这两个注册表项中， <*Computer\_Name*> 表示本地计算机的名称。

## 解决方法

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 但是，注册表修改不当可能会出现严重问题。 因此，按以下步骤操作时请务必谨慎。 出于防范目的，请在修改之前备份注册表，以便在出现问题时还原注册表。 有关如何备份和还原注册表的详细信息，请参阅：[如何备份和还原 Windows 中的注册表](https://support.microsoft.com/help/322756)。

若要解决此问题，请在受影响的计算机上添加缺少的注册表项。 使用注册表编辑器手动创建条目，或打开管理命令提示符窗口，然后运行以下命令：

```
reg add HKLM\SYSTEM\CurrentControlSet\Control\ComputerName\ActiveComputerName /t REG_SZ /v ComputerName /d <Computer_Name> /f
```

注意

在此命令中， <Computer\_Name> 表示本地计算机的名称。

编辑注册表后，重新启动计算机。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/lanmanworkstation-service-doesnt-start-error-2250)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
