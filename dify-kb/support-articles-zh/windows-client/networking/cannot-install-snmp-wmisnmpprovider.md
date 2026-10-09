# 无法在 Windows 10 或 Windows 11 中添加 SNMP 和 WMI SNMP 提供程序功能

本文提供了在 Windows 10 或 Windows 11 中添加简单网络管理协议（SNMP）和 Windows Management Instrumentation （WMI） SNMP 提供程序功能的解决方法。

## 添加 SNMP 和 WMI SNMP 提供程序功能时出错

尝试使用 [部署映像服务和管理（DISM.exe）](/zh-cn/windows-hardware/manufacture/desktop/what-is-dism) 工具在 Windows 10 或 Windows 11 中添加 SNMP 和 WMI SNMP 提供程序功能，如下所示：

```
dism /online /enable-feature /featureName:SNMP /featureName:WMISnmpProvider
```

然后，你会收到以下错误消息：

> 错误：0x800f080c  
> 功能名称 SNMP 未知。  
> 功能名称 WMISnmpProvider 未知。  
> 无法识别 Windows 功能名称。  
> 使用 /Get-Features 选项查找映像中的功能名称，然后重试该命令。

重要

出现此问题的原因是 SNMP 和 WMI SNMP 提供程序功能已弃用。

要解决此问题，请使用下列方法之一。

## 从“设置”页添加 SNMP 和 WMI SNMP 提供程序功能

1. 转到“开始”，选择“**设置>系统”。**

   注意

   在低于 Windows 10 版本 22H2 的版本中，请改为转到**“设置**>**应用”>****应用和功能。**
2. 选择**“可选功能>添加功能”。**

   - 若要添加 SNMP 功能，请选择“**简单网络管理协议”（SNMP）>“添加”。**
   - 若要添加 WMI SNMP 提供程序功能，请选择“ **WMI SNMP 提供程序**>**添加**”。

若要验证添加的状态，请选择“ **查看可选功能历史记录**”。

## 使用 Windows PowerShell 添加 SNMP 和 WMI SNMP 提供程序功能

1. 以管理员身份启动 Windows PowerShell。
2. 运行以下 [Add-WindowsCapability](/zh-cn/powershell/module/dism/add-windowscapability) cmdlet 以添加 SNMP 和 WMI SNMP 提供程序功能。

   ```
   Add-WindowsCapability -Online -Name "SNMP.Client~~~~0.0.1.0"
   ```

   ```
   Add-WindowsCapability -Online -Name "WMI-SNMP-Provider.Client~~~~0.0.1.0"
   ```

若要验证添加的状态，请运行以下 [Get-WindowsCapability](/zh-cn/powershell/module/dism/get-windowscapability) cmdlet。

```
Get-WindowsCapability -Online -Name "SNMP.Client~~~~0.0.1.0"
```

```
Get-WindowsCapability -Online -Name "WMI-SNMP-Provider.Client~~~~0.0.1.0"
```

如果正确添加了这些功能，则状态为 **“已安装** ”。

## 数据收集

如果需要Microsoft支持方面的帮助，建议按照使用 TSS 收集信息中的 [步骤收集用户体验问题](../windows-troubleshooters/gather-information-using-tss-user-experience#wmi)来收集信息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/cannot-install-snmp-wmisnmpprovider)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
