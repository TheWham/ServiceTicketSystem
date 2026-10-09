# 如何在 Windows XP 中重新初始化脱机文件缓存和数据库

本文提供了两种方法，用于在 Windows XP 中重新初始化脱机文件缓存和数据库。

*适用于：* Windows XP  
*原始 KB 数：* 230738

## 总结

脱机文件（CSC 或客户端缓存）缓存和数据库具有可重启的内置功能（如果怀疑其内容已损坏）。 如果怀疑损坏，同步向导可能会返回以下错误消息：

> 无法在 \\**server\_name share\_name\** 上合并脱机更改。 参数不正确。

## 更多信息

### 方法 1

脱机文件缓存是位于 %SystemRoot%\CSC 文件夹中的文件夹结构，默认情况下隐藏该文件夹。 CSC 文件夹及其包含的任何文件和子文件夹不应直接修改;这样做可能会导致数据丢失和脱机文件功能的完整细分。

如果怀疑数据库中损坏，则应使用脱机文件查看器删除文件。 从脱机文件查看器中删除文件后，可以使用同步管理器强制同步文件。 如果缓存仍然未正常工作，可以使用以下过程执行脱机文件重置：

1. 在 **“文件夹选项**”中 **，在“脱机文件** ”选项卡上，按 Ctrl+Shift，然后单击“ **删除文件**”。 以下消息将出现：

   > 将重新初始化本地计算机上的脱机文件缓存。 未与网络上的计算机同步的任何更改都将丢失。 脱机提供的任何文件或文件夹将不再脱机可用。 需要重启计算机。

   是否要重新初始化缓存？
2. 单击“是”两次重启计算机。

### 方法 2

#### 使用注册表编辑器

如果无法访问“ **脱机文件** ”选项卡，请使用此方法通过修改注册表重新初始化系统上的脱机文件（CSC）缓存。 使用此方法还可以在多个系统上重新初始化脱机文件数据库/客户端缓存。 添加以下注册表子项： `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\NetCache`  
键名称：FormatDatabase  
键类型：DWORD  
键值：1

注意

忽略注册表项的实际值。 此注册表更改需要重启。 重启计算机时，shell 将重新初始化 CSC 缓存，然后在注册表项存在时删除注册表项。

警告

删除所有缓存文件并丢失了未同步的数据。

#### 使用Reg.exe

还可以使用Reg.exe命令行编辑器自动执行设置此注册表值的过程。 为此，请在Reg.exe窗口中键入以下命令：

```
REG ADD "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\NetCache" /v FormatDatabase /t REG_DWORD /d 1 /f
```

注意

有关在 Windows Vista 或 Windows 7 中重新初始化脱机文件缓存和数据库的具体步骤，请单击以下文章编号以查看Microsoft知识库中的文章：  
 942974在基于 Windows Vista 或 Windows 7 的客户端计算机上，即使文件服务器已从网络中删除，你仍然可以访问脱机文件。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/re-initialize-offline-files-cache-database)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
