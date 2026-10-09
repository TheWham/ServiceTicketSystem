# 在就地升级 Windows 10 S 后，命令提示符和 PowerShell 不会打开

本文提供了一个解决方案，用于解决命令提示符和 PowerShell 在就地升级 Windows 10 S 后未打开的问题。

*适用于：* Windows 10 版本 1809  
*原始 KB 数：* 4019568

## 症状

Windows 10 S 可以使用各种方法升级到Windows 10 专业版、Windows 10 企业版或Windows 10 教育版。 例如：

- 手动输入产品密钥
- 使用 适用于企业的 Microsoft Store
- 从 Microsoft 应用商店购买许可证
- 使用安装媒体（就地升级）

有关详细信息，请参阅 Windows 10 版本升级 [Windows 10 版本升级](/zh-cn/windows/deployment/upgrade/windows-10-edition-upgrades)。  
使用 Windows 10 安装媒体中的Setup.exe就地升级 Windows 10 S 后，打开命令提示符、PowerShell 或任何 Win32 应用程序时，可能会收到以下错误消息：  
你的组织使用 Device Guard 阻止此应用 C：\Windows\System32\cmd.exe

有关详细信息，请联系支持人员。

![组织使用 Device Guard 阻止此应用错误的屏幕截图。](media/command-prompt-powershell-not-start/organization-used-device-guard-block-app-error.png)

## 原因

出现此问题是因为允许 Windows 10 S 控制 Win32 应用程序的策略尚未清除。

## 解决方法

若要解决此问题，请重新启动计算机。 可能需要重启两三次才能清除此策略。

## 参考

有关 Windows 10 S 中阻止的内容的详细信息，请参阅 [规划 S 模式部署](/zh-cn/windows-hardware/manufacture/desktop/windows-10-s-planning#what-is-blocked-in-windows-10-s)中的 Windows 10。

## 数据收集

如果需要Microsoft支持方面的帮助，建议按照使用 TSS 收集信息中的 [步骤收集用户体验问题](../windows-troubleshooters/gather-information-using-tss-user-experience#powershell)来收集信息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/command-prompt-powershell-not-start)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
