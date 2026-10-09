# 如何在企业中的 Windows 10 上配置 Wi-Fi Sense 和付费 Wi-Fi 服务

本文讨论在 Windows 10 中配置 Wi-Fi Sense 和付费 Wi-Fi 服务的方法。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 3085719

## 总结

Wi-Fi Sense 可以在计算机上自动建立 Wi-Fi 连接，以便你可以在更多位置快速联机。 Wi-Fi Sense 可以将你连接到通过众包收集的 Wi-Fi 热点，或连接到你的联系人通过 Wi-Fi Sense 与你共享的 Wi-Fi 网络。

通过Microsoft商店在热点处购买 Wi-Fi，付费 Wi-Fi 服务使你能够联机。 Windows 将暂时连接到开放热点，以查看付费 Wi-Fi 服务是否可用。

## 详细信息

若要在企业中的计算机上禁用 Wi-Fi Sense 和付费 Wi-Fi 服务，请根据设备管理过程使用以下方法：

[通过 Windows 预配框架进行配置](https://msdn.microsoft.com/library/windows/hardware/mt219718%28v=vs.85%29.aspx)

[通过旧版无人参与的 Windows 设置进行配置（如果企业使用无人参与设置进行预配）](https://msdn.microsoft.com/library/windows/hardware/mt186511%28v=vs.85%29.aspx)

IT 管理员还可以使用组策略禁用 Wi-Fi Sense 和付费 Wi-Fi 服务。

### 对于 Windows 10 版本 1511 或更高版本的 Windows

配置组策略对象**允许 Windows 自动连接到建议的开放热点、联系人共享的网络，以及计算机配置\管理模板\网络\WLAN 服务\WLAN 设置\**下**提供付费服务的**热点。

### 对于早于 Windows 10 版本 1511 的 Windows 版本

配置组策略以创建以下 DWORD 注册表值并将其设置为 **0** 以禁用 Wi-Fi Sense：

`HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\WcmSvc\wifinetworkmanager\config\AutoConnectAllowedOEM`

注意

如果使用组策略禁用 Wi-Fi Sense，则这也禁用以下相关的 Wi-Fi Sense 功能：

- 自动连接到打开热点
- 自动连接到我的联系人共享的网络
- 允许我选择网络来共享我的联系人

TechNet 上提供了详细信息： [注册表扩展](https://technet.microsoft.com/library/cc771589.aspx)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/configure-wifi-sense-and-paid-wifi-service)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
