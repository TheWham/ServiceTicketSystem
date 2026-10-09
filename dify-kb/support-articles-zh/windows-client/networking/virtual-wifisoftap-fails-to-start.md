# 虚拟 WiFi/SoftAP 无法启动并出现错误：无法启动托管网络

本文提供了在启动虚拟 WiFi/SoftAP 时发生的错误（无法启动托管网络）的解决方案。

*适用于：* Windows 7 Service Pack 1、Windows Server 2012 R2  
*原始 KB 数：* 2625519

## 现象

在 Windows 7 和 Windows Server 2008 R2 上，尝试启动虚拟 WiFi/SoftAP 时，可能会收到错误：无法启动托管网络。

## 原因

如果清除无线网络适配器的“允许计算机关闭设备以节省电源”电源选项，则可能会出现这种情况。

## 解决方法

使用以下步骤为无线网络适配器启用“允许计算机关闭设备以节省电源”电源管理选项：

1. 单击“开始”按钮并选择控制面板。
2. 选择“系统和安全性”。
3. 在“系统”下选择设备管理器。
4. 从设备列表中选择并展开网络适配器。
5. 找到无线网络适配器，然后右键单击它，然后选择“属性”。
6. 选择“电源管理”选项卡。
7. 在“电源管理”选项卡下，确保选中以下选项（已启用）： *允许计算机关闭此设备以节省电源*。

注意：如果已控制面板配置为按小图标或大图标查看，则可能看不到步骤 2 中列出的“系统和安全”类别。 在这种情况下，请从可用控制面板小程序中选择“系统”，然后从左窗格中选择设备管理器。 然后，可以跳过步骤 2-3 并继续执行步骤 4。

## 详细信息

Microsoft禁用此电源选项时，Windows 7/Windows Server 2008 R2 不支持虚拟 WiFi/SoftAP。

有关虚拟 WiFi/SoftAP 的详细信息，请参阅以下文章：

[关于无线托管网络](/zh-cn/windows/win32/nativewifi/about-the-wireless-hosted-network)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/virtual-wifisoftap-fails-to-start)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
