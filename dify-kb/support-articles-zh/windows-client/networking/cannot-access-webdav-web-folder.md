# 无法从基于 Windows 的客户端计算机访问 WebDAV Web 文件夹

本文提供了帮助来解决无法从基于 Windows 的客户端计算机访问 Web 分布式创作和版本控制 （WebDAV） Web 文件夹的问题。

*原始 KB 数：* 912152

## 现象

不能从基于 Windows 的客户端计算机访问 WebDAV Web 文件夹。 尝试执行此操作时，可能会遇到以下症状：

- 使用通用命名约定 （UNC） 路径访问 Web 文件夹时，会收到类似于以下内容的错误消息：

  > \\server\webfolder\folder 不可访问。 你可能没有使用此网络资源的权限。  
  > 请联系此服务器的管理员，了解你是否具有访问权限。
  >
  > 附加到系统的设备无法正常工作。
  >
  > 错误 31 = ERROR\_GEN\_FAILURE
- 映射驱动程序信以访问 Web 文件夹时，会收到类似于以下内容的错误消息：

  > 磁盘的格式不正确
  >
  > Windows 无法从此磁盘读取。 磁盘可能已损坏，或者它可能使用与 Windows 不兼容的格式。
- 尝试在命令提示符下枚举 Web 文件夹时，会收到以下错误消息：

  > 找不到文件

此外，每次尝试访问 Web 文件夹时，包含 WebClient 服务的Svchost.exe进程的内存消耗都会增加。 对于 Web 文件夹中每 20,000 个文件，此增加量可能约为 20 MB。 停止 WebClient 服务时不会释放内存。 仅当计算机重新启动时，才会释放内存。

## 原因

如果满足以下所有条件，则可能会出现此问题：

- 客户端计算机正在运行以下配置之一：

  - 具有 Service Pack 1（SP1）和安全更新的 Windows XP 896426
  - Windows XP Service Pack 2 (SP2)
  - Windows XP Professional x64 Edition
  - Windows 7
  - Windows 8
  - Windows 8.1
- WebDAV 文件夹包含许多文件。 例如，文件夹包含 20,000 个或多个文件。 默认情况下，Windows XP 将在一个 Web 文件夹中枚举大约 1,000 个文件。 此数字基于以下注册表子项的默认设置：

  - 路径：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\WebClient\Parameters\`
  - 值：FileAttributesLimitInBytes
  - 数据类型：DWORD
  - 默认值：1,000,000 十进制（1 MB）
  - 说明：此注册表子项确定 WebDAV 重定向程序允许的一个文件夹中所有文件属性的最大集体大小。 此属性限制涵盖所有 PROPFIND 和 PROPPATCH 响应。

出现此问题的原因是 WebDAV 服务器返回的所有文件属性的大小比预期的要大得多。 默认情况下，此大小限制为 1 MB。 此限制出于安全原因。 有关详细信息，请参阅 [从 Web 文件夹中](https://support.microsoft.com/help/900900)下载大于 500000000 字节的文件时的文件夹复制错误消息。

## 解决方法

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 但是，注册表修改不当可能会出现严重问题。 因此，按以下步骤操作时请务必谨慎。 作为额外保护措施，请在修改注册表之前先将其备份。 如果之后出现问题，您就可以还原注册表。 有关如何备份和还原注册表的详细信息，请参阅：[如何备份和还原 Windows 中的注册表](https://support.microsoft.com/help/322756)。

若要解决此问题，请将名为 **FileAttributesLimitInBytes** 的 DWORD 条目添加到以下注册表子项：

`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\WebClient\Parameters\`

将 **FileAttributesLimitInBytes** 注册表值配置为所需的大小，然后重启 WebClient 服务。 为此，请按照下列步骤进行操作：

1. 单击“**开始**”，再单击“**运行**”，键入“*regedit&* ”，然后单击“**确定**”。
2. 找到并单击下面的注册表子项：

   `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\WebClient\Parameters\`
3. 在“编辑”菜单上，指向“新建”，然后单击“DWORD 值”。
4. 键入 **FileAttributesLimitInBytes** 以获取 DWORD 的名称，然后按 Enter。
5. 右键单击 **FileAttributesLimitInBytes**，然后单击“ **修改**”。
6. 在 **“值”数据** 框中，键入要使用的值，然后单击“ **确定**”。 例如，如果 Web 文件夹包含 20,000 个文件，请在*“值”数据**框中键入 20000000。***

   注意

   如果默认值为 1,000,000 （1 MB），Windows 将枚举一个文件夹中最多 1,000 个文件。 文件的实际最大数目可能会有所不同，具体取决于文件属性或文件属性的数量。 默认情况下，WebClient 服务不会请求特定的 WebDAV 属性。 因此，服务器返回所有文件属性。 Microsoft 办公室集成的 Webfolders 重定向程序会请求特定的 WebDAV 属性。
7. 退出注册表编辑器。
8. 停止，然后重启 WebClient 服务。 为此，请按照下列步骤进行操作：

   1. 单击“开始” ，再单击“运行” ，键入 *cmd*，然后单击“确定” 。
   2. 键入以下命令，然后在每个命令后面按 Enter：

      ```
      net stop webclient
      net start webclient
      ```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/cannot-access-webdav-web-folder)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
