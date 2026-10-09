# 从 Microsoft Defender 中排除 UWF 后，Windows 不会启动

本文介绍如何解决从 Microsoft Defender 中排除统一写入筛选器（UWF）后 Windows 不会启动的问题。

*适用于：*Windows 10 企业版、Windows 10 IoT 企业版或Windows 11 企业版

## 问题

假设出现了下面这种情景：

- 在基于Windows 11 企业版、基于Windows 10 企业版或基于Windows 10 IoT 企业版的计算机上启用 UWF 功能。
- 为 Windows Defender 配置 UWF 注册表排除项。 具体而言，写入筛选器中排除了以下注册表项：  
  `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\WdFilter`

在此方案中，计算机在 Windows 启动时停止响应。

注意

- 如果使用命令禁用 UWF 功能 `uwfmgr.exe filter disable` ，则不会出现问题。
- 多次重试后，计算机可能会启动。

此行为是特意这样设计的。 若要解决此问题，请使用替代 menthod 排除 UWF。

## 支持排除 UWF 的方法

若要解决此问题，可以使用 `Registry Commit` Uwfmgr.exe选项来排除 UWF。 此选项可以提交更改以指定值。

以下命令可以提交指定注册表值的更改：

```
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter" Start
```

注意

由于该命令只能指定单个注册表值，因此必须为要提交更改的注册表项指定整个注册表值。

例如，可以在以下屏幕截图中找到类似于值的注册表值。

![注册表编辑器的屏幕截图。](media/windows-hangs-on-startup-after-excluding-uwf-from-microsoft-defender/registry-editor-wdfilter-values.png)

若要提交注册表子项下 `WDFilter` 所做的所有更改，必须运行该 `Registry Commit` 选项，如下所示：

```
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter" DependOnService
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter" Description
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter" DisplayName
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter" ErrorControl
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter" Group
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter" ImagePath
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter" Start
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter" SupportedFeatures
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter" Type
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter\Instances" DefaultInstance
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter\Instances\WdFilter Instance" Altitude
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter\Instances\WdFilter Instance" Flags
uwfmgr.exe registry commit "HKLM\SYSTEM\CurrentControlSet\Services\WdFilter\Security" Security
```

注意

注册表提交选项是一次性操作。 它不会继续通过运行单个命令来绕过写入筛选器。 若要在计算机关闭时提交值更改，必须将此命令设置为关闭脚本。

有关关闭脚本的详细信息，请参阅 [使用本地组策略编辑器](/zh-cn/previous-versions/windows/it-pro/windows-server-2012-R2-and-2012/dn789190(v=ws.11)#how-to-assign-computer-shutdown-scripts)处理启动、关闭、登录和注销脚本。

## 详细信息

若要检查是否从 UWF 注册表筛选器中排除 WDFilter 注册表项，请以管理员身份打开命令提示符窗口，然后在提示符下运行 `uwfmgr.exe get-config` 。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/windows-hangs-on-startup-after-excluding-uwf-from-microsoft-defender)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
