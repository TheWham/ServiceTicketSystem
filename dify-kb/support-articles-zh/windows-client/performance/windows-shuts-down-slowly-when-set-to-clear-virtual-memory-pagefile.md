# 当 Windows 设置为在关闭时清除虚拟内存页文件时，Windows 会慢慢关闭

本文提供了一个解决方案，用于在 Windows 设置为在关闭时清除虚拟内存页文件时缓慢关闭的问题。

*原始 KB 数：* 320423

## 现象

当系统在 Windows Server 2003 和更高版本中打开“清除虚拟内存”页文件时，关闭组策略设置所需的时间可能比通常要长。 此设置称为“关机：清除 Windows Vista 及更高版本中的虚拟内存页面文件”。

## 原因

发生此行为的原因是当启用此策略设置时，计算机必须以物理方式写入页面文件中的每个页面才能清除各个页。 系统清除页面文件所需的时间因页面文件大小和所涉及的磁盘硬件而异。

## Status

此行为是特意这样设计的。

注意

在 Windows XP 和 Windows Server 2003 中打开组策略设置时，也会出现此问题。

## 详细信息

默认情况下，关闭系统关闭组策略设置时清除虚拟内存页文件。 若要在 Windows 2000、Windows XP 或 Windows Server 2003 上确认此设置，请执行以下步骤：

1. 单击“开始”，指向**“设置”**，然后单击控制面板。
2. 双击 **“管理工具”** 。
3. 双击 **“本地安全策略**”。
4. 双击“ **本地策略**”。
5. 单击“安全选项”。
6. 当系统关闭条目时，在清除虚拟内存页文件右侧的 **“有效设置”** 列中查看。

若要在 Windows Vista 和更高版本上检查此设置，请执行以下步骤：

1. 单击“开始”，键入 secpol.msc，然后按 Enter。
2. 展开“本地策略”。
3. 单击“安全选项”。
4. 在 **“关闭”右侧的“安全设置** ”列中查看：清除虚拟内存页文件条目。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/windows-shuts-down-slowly-when-set-to-clear-virtual-memory-pagefile)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
