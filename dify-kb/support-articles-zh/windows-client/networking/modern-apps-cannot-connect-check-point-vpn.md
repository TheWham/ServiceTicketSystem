# 使用 Check Point VPN 连接时，新式应用无法连接

本文提供了使用 Check Point VPN 软件连接到企业网络后新式应用无法连接到 Internet 的问题的解决方案。

*适用于：* Windows 8  
*原始 KB 数：* 2855849

## 现象

假设出现了下面这种情景：

- 使用早于 E80.50 的 Check Point Endpoint 远程访问 VPN 版本。
- 你已成功运行 Windows 8 新式应用程序（应用商店应用）和经典桌面应用程序。
- 可以通过将 Check Point VPN 客户端软件设置为“中心模式”（也就是说，所有流量都通过虚拟网络适配器路由）连接到企业网络。
- 建立连接后，网络状态指示器显示 Internet 连接已完全可用。

在此方案中，经典应用可以成功连接到 Internet。 但是，新式应用无法连接。 此外，如果启用了增强的安全模式，则 Windows Internet Explorer 10 的桌面版本无法连接。

## 原因

出现此问题是因为已安装的防火墙无法设置允许新式应用通过虚拟专用网络进行通信的规则。

## 解决方法

若要解决此问题，请从以下 Check Point 支持中心网站安装 Check Point VPN E80.50（预计 2013 年秋季可用）：

[远程访问 （VPN） 客户端](https://supportcenter.checkpoint.com/supportcenter/portal?eventsubmit_doshowproductpage&producttab=overview&product=175)

## 解决方法

重要

请认真遵循本部分所述的步骤。 如果注册表修改不正确，可能会发生严重问题。 在修改注册表之前，请[备份注册表](https://support.microsoft.com/help/322756)，以便在出现问题时可以还原。

若要解决此问题，请运行以下 Windows PowerShell 脚本来更改注册表中虚拟网络接口的隐藏属性：

```
foreach ($subkey in (gci "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002bE10318} -erroraction silentlycontinue))
{
    if ((get-itemproperty $subkey.pspath).ComponentID eq cp_apvna)
    {
        set-itemproperty $subkey.pspath name Characteristics value 0x1
    }
}
```

本文中提到的第三方产品由 Microsoft 以外的其他公司提供。 Microsoft 不对这些产品的性能或可靠性提供任何明示或暗示性担保。

Microsoft 会提供第三方联系信息来帮助你查找技术支持。 此联系信息可能会更改，恕不另行通知。 Microsoft不能保证此第三方联系信息的准确性。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/modern-apps-cannot-connect-check-point-vpn)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
