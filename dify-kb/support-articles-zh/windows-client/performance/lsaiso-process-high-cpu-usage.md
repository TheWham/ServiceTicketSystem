# Windows 上的 LSAISO 进程中的 CPU 使用率较高

本文提供了 LSAISO 进程在运行 Windows 的计算机上遇到高 CPU 使用率的问题的解决方法。

*适用于：* Windows 10 - 所有版本、Windows 11 - 所有版本、Windows Server 2016、Windows Server 2019、Windows Server 2022  
*原始 KB 数：* 4032786

## 现象

LSAISO（LSA 独立）进程在运行 Windows 10、Windows Server 2016 或更高版本的计算机上遇到高 CPU 使用率。

## 原因

在 Windows 中，LSAISO 进程在称为虚拟安全模式（VSM）的新安全环境中作为独立用户模式（IUM）进程运行。

尝试将 DLL 加载到 IUM 进程、注入线程或传送用户模式 APC 的应用程序和驱动程序可能会破坏整个系统的不稳定。 这种不稳定可能包括“症状”部分中提到的高 LSAISO CPU 方案。

## 解决方法 1：使用消除过程

某些应用程序（如防病毒程序）通常会将 DLL 或队列 APC 注入 LSAISO 进程。 这会导致 LSAISO 进程遇到高 CPU 使用率。

若要进行故障排除，无法将工具附加到 IUM 进程。 这可以防止使用 Windows 调试工具或 WPA\XPERF 在 LSAISO CPU 尖刺期间捕获堆栈跟踪。 因此，此方案中的最佳故障排除方法是使用“消除过程”方法。 为此，请在缓解 CPU 峰值之前禁用应用程序和驱动程序。 确定导致问题的软件后，请联系供应商获取软件更新。 可以引用以下 MSDN 主题中列出的 ISV 建议：

[独立用户模式 （IUM） 进程](/zh-cn/windows/win32/procthread/isolated-user-mode--ium--processes)

注意

在测试 CPU 峰值时，此方法可能需要重启，因为禁用了可疑软件和驱动程序。

## 解决方法 2：检查排队的 APC

下载适用于 Windows 的免费调试工具（WinDbg、KD、CDB、NTSD）。 这些工具包含在 Windows 驱动程序工具包（WDK）和 Windows 驱动程序工具包（WDK）中。 然后，按照以下步骤确定哪个驱动程序正在将 APC 排队到 LSAISO：

1. 在重现 CPU 峰值时，请使用以下 Sysinternals 网站中的NotMyFault.exe等工具生成内核内存转储：

   [Sysinternals 套件](/zh-cn/sysinternals/downloads/sysinternals-suite)

   注意

   不建议使用完整的内存转储，因为在系统上启用 VSM 时需要解密。 若要启用内核转储，请执行以下步骤：

   1. 在**控制面板中打开“系统**”项，然后选择“**高级系统设置**”。
   2. 在**“系统属性**”对话框的**“高级**”选项卡上，选择“启动和恢复**”**区域中的设置****。
   3. 在**“启动和恢复**”对话框中，在“写入调试信息**”**列表中选择内核内存转储****。
   4. **请注意在步骤 5 中使用的转储文件**位置，然后选择“**确定**”。
2. 从适用于 Windows 的调试工具打开WinDbg.exe工具。
3. 在**“文件**”菜单上，单击“符号文件路径**”**，将Microsoft符号服务器的以下路径添加到**“符号路径**”框中，然后选择“**确定**” ：  
   `https://msdl.microsoft.com/download/symbols`
4. 在 **“文件** ”菜单上，单击“ **打开故障转储**”。
5. 浏览到步骤 1d 中记录的内核转储文件的位置，然后选择“ **打开**”。 检查.dmp文件上的日期，以确保此故障排除会话期间新创建该文件。
6. 在 **“命令”** 窗口中，键入 **！apc**，然后按 Enter。

   ![显示 ！apc 的内核转储文件的命令框的屏幕截图。](media/lsaiso-process-high-cpu-usage/type-apc.png)

   输出应类似于以下屏幕截图。

   ![！apc 命令的输出的屏幕截图。在此示例中，名为ProblemDriver.sys的驱动程序列在LsaIso.exe下。](media/lsaiso-process-high-cpu-usage/apc-output.png)
7. 在结果中搜索 **LsaIso.exe**。 如果名为 <ProblemDriver> 的驱动程序.sys列在LsaIso.exe**下**（如步骤 6 中输出的示例屏幕截图所示），请联系供应商，然后参考隔离用户模式 （IUM） 进程[主题中列出的](/zh-cn/windows/win32/procthread/isolated-user-mode--ium--processes)建议缓解措施。

   注意

   如果未在Lsaiso.exe**下**列出任何驱动程序，则表示 LSAISO 进程没有排队的 APC。

## 详细信息

VSM 使用称为虚拟信任级别（VTL）的隔离模式来保护 IUM 进程（也称为 trustlet）。 IUM 进程（如 LSAISO）在 VTL1 中运行，而其他进程在 VTL0 中运行。 在 VTL1 中运行的进程的内存页受 VTL0 中运行的任何恶意代码的保护。

在 Windows 10 和 Windows Server 2016 之前，本地安全机构子系统服务（LSASS）过程只负责管理本地系统策略、用户身份验证和审核，同时它还处理了敏感的安全数据，例如密码哈希和 Kerberos 密钥。

若要使用 VSM 的安全优势，在 VTL1 中运行的 LSAISO trustlet 通过 RPC 通道与在 VTL0 中运行的 LSAISO 进程进行通信。 LSAISO 机密在发送到 LSASS 之前进行加密，LSAISO 的页面会受到 VTL0 中运行的任何恶意代码的保护。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/lsaiso-process-high-cpu-usage)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
