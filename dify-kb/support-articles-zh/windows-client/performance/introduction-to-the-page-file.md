# 页面文件简介

页面文件（也称为“分页文件”）是硬盘上的可选隐藏系统文件。

*适用于：*Windows 10

## 功能

页面文件具有以下功能。

### RAM 的物理扩展

页面文件使系统能够从物理内存中删除不经常访问的修改页面，使系统更有效地使用物理内存，以便更频繁访问的页面。

### 应用程序要求

某些产品或服务出于各种原因需要页面文件。 有关具体信息，请查看产品文档。

例如，以下 Windows 服务器需要页面文件：

- Windows Server 域控制器 （DC）
- DFS 复制 （DFS-R） 服务器
- 证书服务器
- ADAM/LDS 服务器

此要求是因为可扩展存储引擎（ESENT 或 ESE for Microsoft Exchange Server）的数据库缓存算法取决于“\Memory\Transition Pages RePurposed/sec”性能监视器计数器。 需要一个页面文件，以确保如果其他服务或应用程序请求内存，数据库缓存可以释放内存。

对于 Windows Server 2012 Hyper-V 和 Windows Server 2012 R2 Hyper-V，管理 OS（通常称为主机 OS）的页面文件应保留为默认设置“系统托管”。

### 支持系统故障转储

页文件可用于“后退”（或支持）系统故障转储并扩展系统提交的内存（也称为“虚拟内存”）系统可以支持的内存量。

有关系统故障转储的详细信息，请参阅 [系统故障转储选项](configure-system-failure-and-recovery-options#under-write-debugging-information)。

## 在具有大型物理内存的 Windows 中页面文件

安装大型物理内存时，在高峰使用期间，可能不需要页面文件来支持系统提交费用。 例如，64 位版本的 Windows 和 Windows Server 支持的物理内存（RAM）多于 32 位版本支持。 仅可用的物理内存可能足够大。

但是，配置页面文件大小的原因尚未更改。 它一直支持系统故障转储（如有必要）或扩展系统提交限制（如有必要）。 例如，安装大量物理内存时，在高峰使用期间，可能需要一个页面文件来支持系统提交费用。 单独可用的物理内存可能足够大，无法执行此操作。 但是，可能需要页面文件或专用转储文件来备份系统故障转储。

## 系统提交的内存

页面文件扩展了多少“已提交内存”（也称为“虚拟内存”）用于存储修改的数据。

系统提交内存限制是物理内存和所有页面文件的总和。 它表示系统可以支持的最大系统提交内存（也称为“系统提交费用”。

![任务管理器的屏幕截图，其中显示了提交的字节数和提交限制。](media/introduction-to-the-page-file/task-manager-system-commit-memory.png)

注意

在屏幕截图中，提交的字节数（当前正在使用的 Pagefile）为 6.8 GB，提交限制（当前正在使用的 RAM+Pagefile）为 6.8 GB，提交限制（RAM+Pagefile 总计）为 37.7 GB。

系统提交费用是系统中所有已提交的虚拟内存的已提交或“承诺”内存总量。 如果系统提交费用达到系统提交限制，则系统和进程可能无法获得提交的内存。 这种情况可能会导致冻结、崩溃和其他故障。 因此，请确保将系统提交限制设置为足够高，以在高峰使用期间支持系统提交费用。

![内存不足警告的屏幕截图。](media/introduction-to-the-page-file/out-of-memory.png)

![“任务管理器”窗口的屏幕截图，其中打开了“性能”选项卡，其中显示了系统提交的费用和系统提交的限制。](media/introduction-to-the-page-file/task-manager-commit.png)

系统提交的费用和系统提交的限制可以在任务管理器中的“性能**”选项卡上或使用“\Memory\Committed Bytes”和“\Memory\Commit Limit”性能计数器来度量**。 \Memory\% Committed Bytes In Use counter is a ratio of \Memory\Committed Bytes to \Memory\Commit Limit values.

注意

当系统提交费用达到系统提交限制的 90% 时，系统管理的页文件会自动增长到物理内存或 4 GB（无论大小大于，但不超过卷大小的一分之一）。 这假设有足够的可用磁盘空间来适应增长。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/introduction-to-the-page-file)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
