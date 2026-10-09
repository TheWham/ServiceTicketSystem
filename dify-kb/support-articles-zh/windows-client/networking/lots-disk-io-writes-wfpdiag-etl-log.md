# Windows 中的端口扫描防护筛选器行为

本文介绍 Windows Server 2008 及更高版本中端口扫描防护筛选器的功能。 它还包括一种解决方法，用于在 wfpdiag.etl 日志中存在活动时生成大量磁盘 I/O 的按设计行为。

*原始 KB 数：* 3044882

## 现象

假设出现了下面这种情景：

- 服务器上安装了自定义网络应用程序。
- 应用程序捕获网络上的大量流量。
- 服务器可能使用 DHCP 分配的 IP 地址。

在此方案中，当写入 C：\Windows\System32\wfp\wfp\wfpdiag.etl 日志时，可能会生成大量的磁盘 I/O。

## 原因

此为有意行为。 触发端口扫描防护筛选器时，这通常意味着没有侦听端口的进程。 （出于安全原因，WFP 会阻止进程侦听。在没有侦听器的端口上尝试连接时，WFP 会将数据包识别为来自端口扫描程序，因此会无提示地删除连接。

如果存在侦听器，并且由于数据包格式不正确或身份验证而阻止了通信，则丢弃的事件将列为“DROP”（不无提示），而 WFP 日志记录将指示不同的筛选器 ID 和名称。

此筛选器内置于 Windows 防火墙和高级安全性（WFAS）。 它包含在 Windows Vista、Windows Server 2008 和更高版本的 Windows 中。

## 解决方法

若要解决此问题，请使用以下方法之一禁用 WFP 日志记录：

- 通过从提升的命令提示符运行以下 Netsh 命令来禁用 WFP 日志记录：

  ```
  netsh wfp set options netevents=off
  ```
- 在注册表中禁用 WFP 日志记录。 为此，请按照下列步骤进行操作：

  1. 启动“注册表编辑器”。
  2. 找到以下注册表子项： `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\BFE\Parameters\Policy\Options`
  3. 右键单击子项，单击“新建**”**，然后创建 DWORD（32 位）注册表值。
  4. 键入 *CollectNetEvents* 作为注册表值名称。
  5. 将值数据保留为 0。
  6. 重新启动服务器。

注意

通过禁用 WFP 日志记录，这只会停止在 wfpdiag.etl 中记录 WFP 活动。 端口扫描防护筛选器继续正常工作。

## 详细信息

有关详细信息，请参阅 [具有高级安全性](/zh-cn/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/dd448557(v=ws.10))的 Windows 防火墙中的隐藏模式。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/lots-disk-io-writes-wfpdiag-etl-log)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
