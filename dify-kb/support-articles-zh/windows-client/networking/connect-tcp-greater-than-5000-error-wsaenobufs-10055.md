# 尝试从大于 5000 的 TCP 端口进行连接时，会收到错误“WSAENOBUFS （10055）”

尝试从大于 5000 的 TCP 端口进行连接时，本文有助于修复错误“WSAENOBUFS （10055）。

*原始 KB 数：* 196271

## 现象

如果尝试从大于 5000 的端口设置 TCP 连接，则本地计算机会使用以下 WSAENOBUFS （10055） 错误消息进行响应：

> 无法对套接字执行操作，因为系统缺少足够的缓冲区空间或队列已满。

## 解决方法

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 但是，注册表修改不当可能会出现严重问题。 因此，按以下步骤操作时请务必谨慎。 作为额外保护措施，请在修改注册表之前先将其备份。 如果之后出现问题，您就可以还原注册表。 有关如何备份和还原注册表的详细信息，请单击下面的文章编号，查看相应的 Microsoft 知识库文章：  
[322756](https://support.microsoft.com/help/322756) 如何备份和还原 Windows 中的注册表

默认的最大临时 TCP 端口数是“适用于”部分中包含的产品中的 5000 个。 这些产品中添加了一个新参数。 若要增加临时端口的最大数目，请执行以下步骤：

1. 启动“注册表编辑器”。
2. 在注册表中找到以下子项，然后单击“参数：

   HKEY\_LOCAL\_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters
3. 在**“编辑**”菜单上，单击“新建**”**，然后添加以下注册表项：  
   值名称：MaxUserPort  
   值类型：DWORD 值数据：65534 有效范围：5000-65534 （小数） 默认值：0x1388 （5000 decimal） 说明：此参数控制程序从系统请求任何可用用户端口时使用的最大端口号。 通常，临时（短期）端口在 1024 和 5000（含 5000）的值之间分配。 在发布安全公告 MS08-037 后，Windows Server 2003 的行为已更改为与 Windows Server 2008 和 Windows Vista 的行为更接近。 有关Microsoft安全公告 MS08-037 的详细信息，请单击以下文章编号以查看Microsoft知识库中的文章：

   951746 MS08-037：Windows Server 2008、Windows Server 2003 和 Windows 2000 Server 中 DNS 安全更新的说明：2008 年 7 月 8 日

   951748 MS08-037：Windows Server 2003、Windows XP 和 Windows 2000 Server 中 DNS 安全更新的说明（客户端）：2008 年 7 月 8 日

   [953230](https://support.microsoft.com/help/953230) MS08-037：DNS 中的漏洞可能允许欺骗
4. 退出注册表编辑器，然后重启计算机。

   注意

   其他 TCPTimedWaitDelay 注册表参数确定关闭端口等待多长时间，直到可以重复使用关闭的端口。

## 详细信息

有关相关主题的详细信息，请访问以下Microsoft网站：

<https://technet.microsoft.com/library/bb726981.aspx>  
有关相关主题的详细信息，请单击以下文章编号以查看Microsoft知识库中的文章：

314053 Windows XP 的 TCP/IP 和 NBT 配置参数

### 对基于 x64 的 Microsoft Windows 版本的技术支持

如果硬件随已安装的 Microsoft Windows x64 版本一起提供，则硬件制造商会为 Windows x64 版本提供技术支持和帮助。 在这种情况下，硬件制造商会提供支持，因为硬件已随附 Windows x64 版本。 硬件制造商可能使用单独组件自定义了 Windows x64 版本的安装。 单独组件可能包括特定设备驱动程序，也可以包括可选设置以最大限度提高硬件性能。 如果必须具有 Windows x64 版本的技术帮助，Microsoft将提供合理的努力帮助。 但是，你可能需要直接与制造商联系。 制造商最有资格为他们在硬件上安装的软件提供支持。 如果你单独购买了 Windows x64 版本（如 Windows Server 2003 x64 版本），请联系Microsoft获取技术支持。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/connect-tcp-greater-than-5000-error-wsaenobufs-10055)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
