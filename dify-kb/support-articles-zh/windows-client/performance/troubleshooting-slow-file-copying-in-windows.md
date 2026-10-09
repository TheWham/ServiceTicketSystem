# 排查 Windows 中文件复制速度缓慢的问题

本文可帮助管理员诊断和解决组织中文件复制速度缓慢的问题。

*原始 KB 数：* 10118

## 确定问题的原因

文件复制速度缓慢可能会导致存储问题、客户端问题和服务器问题。

在托管共享文件夹的文件服务器上，将该文件复制到其本地硬盘。 如果文件复制速度异常低（比平均速度慢得多），请尝试更新存储的驱动程序。 如果问题仍然存在，请联系驱动程序制造商进一步进行故障排除。

如果速度正常，请使用另一台客户端计算机从共享文件夹或共享文件夹复制文件。

- 如果文件复制速度仍然缓慢，请参阅 [服务器端故障排除](#server-side-troubleshooting)。
- 如果未出现问题，请参阅 [客户端故障排除](#client-side-troubleshooting)。

## 客户端故障排除

让我们验证共享文件夹的类型。 为此，请打开共享文件夹的属性。 对于分布式文件系统（DFS）共享文件夹， **将显示 DFS** 选项卡。

![共享文件夹属性窗口中 DFS 选项卡的屏幕截图。](media/troubleshooting-slow-file-copying-in-windows/dfs-tab.png)

### 共享文件夹是 DFS 共享文件夹

让我们确定问题是否由 DFS 路径引起。 尝试使用 UNC 路径而不是 DFS 路径打开共享文件夹。 然后，可以检查问题是否仍然存在。 此步骤可以帮助你确定问题是否由 DFS 路径引起。
如何确定 DFS 共享文件夹的 UNC 路径：

1. 右键单击共享文件夹，然后选择“ **属性**”。
2. 在 **DFS** 选项卡上，可以看到引荐列表中的 **UNC 路径**。

   ![共享文件夹属性窗口中 DFS 选项卡的屏幕截图，其中显示了引荐列表中的 UNC 路径。](media/troubleshooting-slow-file-copying-in-windows/referral-list.png)

如果在使用 UNC 路径时速度仍然缓慢，则复制单个文件、文件夹或多个文件时[，会看到](#slow-performance-occurs-when-you-copy-a-single-file-a-folder-or-multiple-files)性能缓慢。

如果使用 UNC 路径时未发生此问题，请按照以下步骤验证 DFS 引荐。

#### 验证 DFS 引荐

1. 右键单击共享文件夹，然后选择“ **属性**”。 在 **DFS** 选项卡上，找到所有活动引荐。
2. 删除非活动或无法访问或已删除的 UNC 路径。
3. 逐个连接这些路径，并确保可以直接从客户端访问所有目标路径。 根据设计，如果客户端无法连接第一个引荐，它将切换到第二个引荐，依此推。 它将创建延迟。

如果问题仍未解决，请参阅 [服务器端故障排除](#server-side-troubleshooting)。

### 共享文件夹不是 DFS 共享文件夹

检查文件复制速度缓慢的问题何时发生。

#### 仅当复制文件夹或多个文件时，才会降低性能

如果将包含多个文件的复制时间与相同大小的文件的复制时间进行比较，则复制文件夹将始终需要更多时间。 此行为在意料之中。 文件夹中的文件越多，文件复制过程越慢。

#### 复制单个文件、文件夹或多个文件时性能降低

若要解决此问题，请在存在问题的客户端计算机上执行以下步骤：

1. [从客户端计算机](/zh-cn/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/cc732472(v=ws.10))中删除第三部分网络提供程序。 默认选项如下所示。 （任何其他提供商都可以视为第三方。

   ![“高级设置”窗口中的“提供程序顺序”选项卡的屏幕截图，其中显示了网络提供程序的默认选项。](media/troubleshooting-slow-file-copying-in-windows/network-provider.png)
2. 从以下注册表项中删除其他值。 为此，请打开注册表编辑器。 找到以下键。 每个键都包含提供程序订单值。
   `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\NetworkProvider\HwOrder`
   `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\NetworkProvider\Order`  
   检查以确保每个提供程序订单值只有三个值：“`RDPNP`”、“”、“`LanmanWorkstation`”和“`webclient`.

   ![上述注册表项的“编辑字符串”对话框的屏幕截图。](media/troubleshooting-slow-file-copying-in-windows/edit-string.png)
3. 将 Jumbo Frames **和 **Large 发送卸载**的设置**与工作计算机上的设置进行比较。 并相应地调整 Jumbo Frames **和 **Large 发送卸载**的设置**。 （如果它已禁用，请启用它，然后检查它是否有帮助）

   ![网络适配器属性的“高级”选项卡中 Jumbo Packet 设置的屏幕截图。](media/troubleshooting-slow-file-copying-in-windows/jumbo-packet-settings.png)
4. 确保工作站服务正在运行。
5. 确保在 **网络连接属性中选择用于Microsoft网络的** 客户端。

   ![“本地区域连接属性”对话框的屏幕截图，其中选择了“Microsoft网络客户端”项。](media/troubleshooting-slow-file-copying-in-windows/client-microsoft-networks.png)

## 服务器端故障排除

安装承载共享文件夹的文件服务器的修补程序。

对于 Windows Server 2008 或 Windows 7，请安装 KB 2473205[中所述](https://support.microsoft.com/kb/2473205)的所有修补程序。  
对于 Windows Server 2012 或 Windows 8，请安装 KB 2899011[中所述](https://support.microsoft.com/kb/2899011)的所有修补程序。

如果问题未解决，请执行以下步骤来排查该问题：

1. 检查客户端是否已连接到远程/WAN DFS 服务器。 （理想情况下，它应连接到本地站点 DFS 服务器）。 如果已连接，请仔细检查 **Active Directory 站点和服务中的站点和子网** 映射。 如果子网未正确映射，则 DFS 会在提供引荐时为远程 DFS 服务器提供不正确的优先级。
2. 确保本地 DFS 服务器正常工作。
3. [在引荐](/zh-cn/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/cc732414(v=ws.11))中设置目标的排序方法。
4. 如果在环境中启用了 IPv6，请在 Active Directory 站点和服务中配置 IPv6 子网。 或者，作为一种解决方法，请在环境中禁用 IPv6。

如何确定客户端连接到的引荐 DFS 服务器：

1. 在客户端计算机上，右键单击共享文件夹，然后选择“ **属性**”。
2. 在 **DFS** 选项卡上，检查引荐列表。 当前 DFS 服务器标记为活动。 在以下示例中，客户端连接到服务器 HAOMS1。

   ![客户端计算机上共享文件夹属性窗口中 DFS 选项卡的屏幕截图，其中显示了引荐列表中的 UNC 路径。](media/troubleshooting-slow-file-copying-in-windows/referral-list.png)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/troubleshooting-slow-file-copying-in-windows)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
