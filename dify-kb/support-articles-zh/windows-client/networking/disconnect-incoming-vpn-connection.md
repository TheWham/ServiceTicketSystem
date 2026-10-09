# 如何断开传入 VPN 连接的连接

本文介绍如何在“查看可用网络”对话框中未显示用于断开传入 VPN 连接的选项时断开传入 VPN 连接。

*原始 KB 数：* 2737610

注意

右键单击 Windows Server 2012 中的传入 VPN 连接，然后单击“ **连接/断开连接**”时， **将显示“查看可用网络** ”对话框。 但是，不显示断开传入 VPN 连接连接的选项。

## 详细信息

若要断开传入 VPN 连接的连接，请执行以下步骤：

1. 打开网络连接。 为此，请使用下列任一方法：

   - 从屏幕右边缘轻扫，或指向屏幕右下角，然后单击“ **搜索”。** 然后，键入ncpa.cpl，然后单击 **Ncpa.cpl** 图标。
   - 按 Win+R 打开 **“运行”** 窗口，键入ncpa.cpl，然后单击“ **确定**”。
2. 右键单击要断开连接的传入 VPN 连接，然后单击“ **状态**”。
3. 在 **“常规** ”选项卡上，单击“ **断开连接**”。
4. 关闭网络连接。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/disconnect-incoming-vpn-connection)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
