# 使用网络监视器收集数据

本文介绍如何使用Microsoft网络监视器 3.4，这是捕获网络流量的工具。

*适用于：*Windows 10

注意

网络监视器是已存档的协议分析器，不再正在开发中。 此外，Microsoft消息分析器（MMA）已停用，其下载包已于 2019 年 11 月 25 日从 microsoft.com 站点中删除。 目前尚未开发 Microsoft Message Analyzer 的 Microsoft 替代品。 对于类似的功能，请考虑使用另一个非Microsoft网络协议分析器工具。 有关详细信息，请参阅 [Microsoft消息分析器操作指南](/zh-cn/message-analyzer/microsoft-message-analyzer-operating-guide)。

若要开始， [请下载网络监视器工具](https://www.microsoft.com/download/details.aspx?id=4865)。 安装网络监视器时，它会安装其驱动程序，并将其挂钩到设备上安装的所有网络适配器。 可以在适配器属性上看到相同的内容，如下图所示：

![网络适配器属性的屏幕截图。](media/collect-data-using-network-monitor/network-monitor-adapters.png)

在安装过程中驱动程序连接到网络接口卡（NIC）时，将重新初始化 NIC，这可能会导致短暂的网络故障。

## 捕获流量

1. 选择“**以管理员**身份运行”，以提升状态运行`netmon`。

   ![Netmon 的“开始”搜索结果的屏幕截图。](media/collect-data-using-network-monitor/nm-start.png)
2. 此时会打开网络监视器，并显示所有网络适配器。 选择要捕获流量的网络适配器，选择“新建捕获**”**，然后选择“**开始**”。

   ![网络监视器菜单上“新建捕获”选项的屏幕截图。](media/collect-data-using-network-monitor/nm-new-capture.png)
3. 重现问题，你将看到网络监视器在网络上捕获数据包。

   ![网络数据包的帧摘要的屏幕截图。](media/collect-data-using-network-monitor/network-monitor-frame-summary.png)
4. 选择“停止**”**，然后转到“**文件>另存为**”以保存结果。 默认情况下，该文件将另存为 `.cap` 文件。

保存的文件捕获了本地计算机上的所选网络适配器传入和传出的所有流量。 但是，你的兴趣只是调查与你面临的特定连接问题相关的流量/数据包。 因此，需要筛选网络捕获才能仅查看相关流量。

## 常用筛选器

- Ipv4.address==“client ip” and ipv4.address==“server ip”
- Tcp.port==
- Udp.port==
- Icmp
- Arp
- Property.tcpretranmits
- Property.tcprequestfastretransmits
- Tcp.flags.syn==1

提示

如果要筛选特定字段的捕获，并且不知道该筛选器的语法，只需右键单击该字段并选择“ **将所选值添加到显示筛选器**”。

使用 `netsh` 内置于 Windows 的命令收集的网络跟踪是扩展“ETL”。 但是，可以使用网络监视器打开这些 ETL 文件以供进一步分析。

## 详细信息

- [使用网络监视器 3.0 进行筛选简介](/zh-cn/archive/blogs/netmon/intro-to-filtering-with-network-monitor-3-0)
- [网络监视器筛选器示例](https://blogs.technet.microsoft.com/rmilne/2016/08/11/network-monitor-filter-examples/)
- [网络监视器无线筛选](https://social.technet.microsoft.com/wiki/contents/articles/1900.network-monitor-wireless-filtering.aspx)
- [网络监视器 TCP 筛选](https://social.technet.microsoft.com/wiki/contents/articles/1134.network-monitor-tcp-filtering.aspx)
- [网络监视器对话筛选](https://social.technet.microsoft.com/wiki/contents/articles/1829.network-monitor-conversation-filtering.aspx)
- [如何使用网络监视器工具设置和收集网络捕获](/zh-cn/archive/blogs/msindiasupp/how-to-setup-and-collect-network-capture-using-network-monitor-tool)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/collect-data-using-network-monitor)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
