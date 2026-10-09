# 内存分配错误可能是页面文件增长缓慢导致的

本文为应用程序频繁分配内存时发生的错误提供了一种解决方法。

*适用于：* Windows 10、Windows 11  
*原始 KB 数：* 4055223

## 现象

频繁分配内存的应用程序可能会遇到随机的“内存不足”错误。 此类错误可能会导致受影响的应用程序出现其他错误或意外行为。

## 原因

内存分配失败的原因可能是由于与页面文件的大小增加相关的延迟，以支持系统中的其他内存要求。 这些失败的一个潜在原因是页面文件大小配置为“自动”。自动页面文件大小以小页面文件开头，并根据需要自动增长。

IO 系统包含许多组件，包括文件系统筛选器、文件系统、卷筛选器、存储筛选器等。 给定系统上的特定组件可能会导致页面文件增长的可变性。

## 解决方法

若要解决此问题，请手动配置页面文件的大小。 为此，请按照下列步骤进行操作：

1. 按 Windows 徽标键 + 暂停/中断键以打开 **系统属性**。
2. 选择**“高级系统设置”**，然后在“高级**”选项卡上的**“性能**”部分中选择“**设置****”。
3. 选择**“高级**”选项卡，然后选择“虚拟内存**”部分中的**“**更改**”。
4. 清除“ **为所有驱动器** 自动管理分页文件大小”复选框。
5. 选择“ **自定义大小**”，然后设置分页文件的“初始大小”和“最大大小”值。 建议将初始大小设置为系统中 RAM 量 1.5 倍。
6. 选择“确定**”**以应用设置，然后重启系统。
   如果继续收到“内存不足”错误消息，请增加页面文件的“初始大小”。

## Status

Microsoft已确认这是 Windows 10 中的问题。

## 详细信息

如果使用 Microsoft Visual C++ 编译器（cl.exe）：可能会遇到此问题，可能会出现间歇性生成错误，如下所示：

- 错误 C1076：编译器限制：达到内部堆;使用 /Zm 指定更高的限制
- 错误 C1083：无法打开typefile： 'file'： message
- 错误 C1090：PDB API 调用失败，错误代码“code”： 'message'
- 编译器错误 C3859：超出 PCH 的虚拟内存范围;请使用“-ZmXXX”或更高版本的命令行选项重新编译

有关 Visual C++ 编译器错误以及如何解决这些问题的详细信息，请参阅 [预编译标头（PCH）问题和建议](https://devblogs.microsoft.com/cppblog/precompiled-header-pch-issues-and-recommendations/)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/slow-page-file-growth-memory-allocation-errors)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
