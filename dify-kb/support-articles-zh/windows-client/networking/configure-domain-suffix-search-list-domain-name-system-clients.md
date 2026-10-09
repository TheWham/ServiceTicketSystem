# 如何在域名系统客户端上配置域后缀搜索列表

本文介绍如何在域名系统（DNS）客户端上自动配置域后缀搜索列表的过程。

注意

本文适用于 Windows 2000。 对 Windows 2000 的支持将于 2010 年 7 月 13 日结束。 Windows 2000 支持终止解决方案中心是规划 Windows 2000 迁移策略的起点。 有关详细信息，请参阅 [Microsoft 支持生命周期策略](/zh-cn/lifecycle/)。

*原始 KB 数：* 275553

## 总结

本文不介绍如何在客户端上配置域后缀搜索列表。 本文仅介绍如何分发大规模域后缀搜索列表。

## 更多信息

Microsoft Windows 2000 的典型名称解析过程使用主 DNS 后缀和任何特定于连接的 DNS 后缀。 如果这些后缀不起作用，则名称解析过程会尝试主 DNS 后缀的下放。

在客户端上配置域后缀搜索列表时，仅使用该列表。 不使用主 DNS 后缀和任何特定于连接的 DNS 后缀，也不会尝试主要后缀的下放。 域后缀搜索列表是所有标准域名解析程序（DNR）查找机制的管理替代。

有关如何使用 DNS 后缀的详细信息，请转到 Windows 2000 帮助并查看“配置客户端设置”主题（位于“网络/DNS/概念”/“使用 DNS/管理客户端/”文件夹）。

### 将域后缀搜索列表推送到 DNS 客户端

以下分发方法可用于将域后缀搜索列表推送到 DNS 客户端：

- Regini.exe。 Microsoft Windows 2000 资源工具包中的Regini.exe工具可用于将域后缀搜索列表设置放入注册表中。 本文的“示例 Regini 脚本”部分提供了示例 Regini 脚本。
- 无人参与安装。 可以在无人参与安装期间填充域后缀搜索列表设置。

以下分发方法不适用于将域后缀搜索列表推送到 DNS 客户端：

- 动态主机配置协议 (DHCP)。 无法将 DHCP 配置为发送域后缀搜索列表。 MICROSOFT DHCP 服务器当前不支持此操作。
- Netsh （Netshell）。 Netsh 实用工具没有用于设置或更改域后缀搜索列表的命令。
- 组策略。 在 Windows 2000 中，组策略没有用于分发域后缀搜索列表的机制。 但是，Windows Server 2003 包含此功能。
- Microsoft Visual Basic 脚本版（VBScript）。 没有可用于编写更改域后缀搜索列表脚本的应用程序编程接口（API）。

### 示例 Regini 脚本

使用以下两行文本创建文本文件，并将其另存为Suffix.txt文件。 以下间距必须完全如上所示，其中 `adatum.xxx` 表示域后缀。 最多可以指定六个域后缀。 搜索顺序从左到右。

`\Registry\Machine\System\CurrentControlSet\Services\TCPIP\Parameters`  
`SearchList="testadatum.com,test2adatum.net,test3adatum.gov"`

将Regini.exe和Suffix.txt文件复制到上述位置，并运行 regini.exe suffix.txt 命令。

脚本更新注册表后，必须重新启动计算机才能更新设置。

若要运行脚本，必须具有对计算机的管理员或系统级访问权限。

注意

另一种方法是使用Microsoft Windows 脚本主机：

1. 创建扩展名为 .vbs 的文件（例如 C：\add.vbs）。
2. 将以下两行添加到文件中：

   ```
   SET WSHShell = CreateObject("WScript.Shell")
   WSHShell.RegWrite "HKLM\System\CurrentControlSet\Services\TCPIP\Parameters\SearchList", "testadatum.com,test2adatum.net,test3adatum.gov", "REG_SZ"
   ```

   （第二行以“WSHShell.RegWrite”开头，以“REG\_SZ”结尾）
3. 双击要运行的文件或在命令提示符处键入 *C：\add.vbs*

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/configure-domain-suffix-search-list-domain-name-system-clients)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
