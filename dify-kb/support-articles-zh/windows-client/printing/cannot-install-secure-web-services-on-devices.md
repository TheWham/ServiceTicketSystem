# 无法使用打印管理控制台安装安全的 Web Services on Devices（WSD）打印机

本文帮助修复以下问题：无法使用"搜索网络中的打印机"从打印管理控制台（PrintManagement.msc）安装安全的 Web Services on Devices（WSD）打印机。

_适用于：_ &nbsp; Windows 7 Service Pack 1, Windows Server 2008 R2 Service Pack 1  
_原始 KB 编号：_ &nbsp; 2701603

## 症状

请考虑以下情形：

- 你有一台始终通过 SSL 连接进行连接的安全 Web Services on Devices（WSD）打印机。
- 你无法使用"搜索网络中的打印机"从打印管理控制台（PrintManagement.msc）安装该打印机。

在此情形下，你尝试通过以下步骤安装打印机：

1. 打开打印管理控制台（`PrintManagement.msc`）
2. 在左窗格中展开**打印服务器** > 服务器名称 > **打印机**
3. 右键单击**打印机**
4. 选择**添加打印机...**
5. 选择**搜索网络中的打印机**
6. 在**网络打印机搜索结果**中选择**安全 WSD 打印机**。
7. 单击**下一步**
8. 单击**下一步**开始安装。

## 原因

打印管理控制台中的"搜索网络中的打印机"无法正确使用 SSL 与打印机通信。

## 解决方案

你可以通过以下方法安装安全的 Web Services on Devices（WSD）打印机：

方法 1：在"设备和打印机"中使用"使用 TCP/IP 地址或主机名添加打印机"

1. 单击"开始"，然后单击"设备和打印机"
2. 运行"添加打印机"向导
3. 单击"添加网络、无线或 Bluetooth 打印机"
4. 单击"我需要的打印机不在列表中"
5. 选择"使用 TCP/IP 地址或主机名添加打印机"，然后单击"下一步"按钮
6. 输入打印机的主机名或 IP 地址

方法 2：在打印管理控制台中使用"按 IP 地址或主机名添加 TCP/IP 或 Web 服务打印机"

1. 打开打印管理控制台（PrintManagement.msc）
2. 在打印管理控制台中，右键单击"打印机"，然后单击"添加打印机"
3. 网络打印机安装向导启动
4. 单击"按 IP 地址或主机名添加 TCP/IP 或 Web 服务打印机"，然后单击"下一步"
5. 输入打印机的主机名或 IP 地址（端口名默认与之相同），然后单击"下一步"
6. 对打印机名称、联系信息或共享状态进行必要的更改，然后单击"下一步"

## 更多信息

[Web Services on Devices（WSD）路线图](https://msdn.microsoft.com/library/bb756908.aspx)

## 数据收集

如果需要 Microsoft 支持部门的帮助，建议你按照[使用 TSS 收集用户体验问题的信息](https://learn.microsoft.com/en-us/troubleshoot/windows-client/windows-troubleshooters/gather-information-using-tss-user-experience#printing)中提到的步骤收集信息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/cannot-install-secure-web-services-on-devices)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
