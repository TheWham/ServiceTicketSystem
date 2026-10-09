# 通过移动运营商进行无线更新后，设备无法连接到移动宽带

本文提供了一个解决方法，说明设备在从移动运营商进行无线更新后无法连接到移动宽带的问题。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 3160433

## 现象

基于 Windows 10 的设备过去可以连接到移动宽带，但在移动运营商向设备应用无线更新后，连接尝试会失败。 此问题仅影响与移动运营商合作伙伴有特殊计划的企业客户。

## 原因

如果移动运营商直接对调制解调器进行了无线更新，则会出现此问题。 Windows 会尝试根据以前的成功连接使用操作系统中的配置建立连接。 但是，移动运营商网络和调制解调器可能会阻止来自 Windows 的连接请求，因为 Windows 请求与调制解调器中的配置不匹配。

## 解决方法

警告

在应用以下方法之前，请检查你的 Windows 版本以确保正在运行 Windows 10 版本 10586.420 或更高版本。 为此，请按 Window 键 + R，然后键入 winver。 如果未运行内部版本 10586.420 或更高版本，请将 Windows 安装更新到最新的可用版本。

若要解决“症状”部分中介绍的问题，请执行以下步骤：

1. 按 Windows 键 + R，然后键入 regedit，打开注册表编辑器。
2. 导航到 HKEY\_LOCAL\_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\控制面板\Settings\Network。
3. 右键单击 **网络** 密钥，然后单击“ **权限**”。
4. 单击“高级**”**，检查所有者是否为 **TrustedInstaller**。
5. 单击“更改”链接，然后输入 <**machine\_name**>\Administrators。
6. 单击“检查名称**”**以验证<**machine\_name**>\管理员是否已正确验证（带下划线）。 例如： *MY-LAPTOP\Administrators*。 如果是，请单击“ **确定**”。

   如果 **检查名称** 未返回带下划线的名称，则用户名的格式不正确。
7. 在“网络高级安全设置”窗格中单击“**确定****”。**
8. 选择**“管理员**”，在“允许**”列中选中**“完全控制**”复选框**，然后单击“**确定**”。
9. 创建或找到以下注册表项，并将 DWORD 值设置为 1（DWORD=1）：

   `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Control Panel\Settings\Network\ManualConnectionRetry`
10. 转到**“设置”**->**“网络”和“Internet**-**>手机网络**->**连接”。**
11. 重试页，类似于：

![网络和 Internet 设置的“手机网络”页中移动运营商网络连接重试选项的屏幕截图。](media/device-cant-connect-mobile-broadband-over-the-air/network-and-internet.png)

12. 单击 **“是”** 。  
    Windows 现在可以使用调制解调器中的配置进行连接。 此调制解调器配置覆盖操作系统上的现有配置。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/device-cant-connect-mobile-broadband-over-the-air)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
