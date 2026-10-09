# 保存和还原现有 Windows 共享

本文提供有关保存和还原现有 Windows 共享的一些信息。

*原始 KB 数：* 125996

## 总结

如果需要完成以下任一过程，可以保存原始Microsoft Windows 安装上存在的共享名称，包括分配给这些共享的任何权限：

- 通过现有安装重新安装 Windows（全新安装，而不是升级）。
- 将所有数据驱动器从一台服务器移到另一台服务器。
- 将 Windows 安装到已安装 Windows 的计算机上的另一个文件夹或驱动器。

## 详细信息

有关管理员如何安全地将数据从一个文件服务器迁移到另一个文件服务器的信息，请访问以下Microsoft网站：  
[Microsoft文件服务器迁移工具包](https://www.microsoft.com/windowsserver2008/en/us/fsmt.aspx)。

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 但是，注册表修改不当可能会出现严重问题。 因此，按以下步骤操作时请务必谨慎。 作为额外保护措施，请在修改注册表之前先将其备份。 如果之后出现问题，您就可以还原注册表。 有关如何备份和还原注册表的详细信息，请单击以下文章编号以查看Microsoft知识库中的文章： [322756](https://support.microsoft.com/help/322756) 如何在 Windows 中备份和还原注册表。

若要仅保存现有共享名称及其在 Windows 上的权限，请执行以下步骤。

注意

此过程仅适用于 NetBIOS 共享，不适用于 Macintosh 卷。

1. 在包含要保存的共享名称和权限的现有 Windows 安装上，启动 **注册表编辑器** （Regedt32.exe）。
2. 在HKEY\_LOCAL\_MACHINE子树中，转到以下键：  
   `SYSTEM\CurrentControlSet\Services\LanmanServer\Shares`。
3. 保存或导出注册表项。

   - 对于 Windows NT 和 Windows 2000，请单击注册表菜单上的“ **保存密钥** ”。
   - 对于 Windows Server 2003，请单击“文件**”菜单上的**“**导出**”。
4. 键入新的文件名（不需要文件扩展名），然后将该文件保存到软盘。
5. 重新安装 Windows。
6. 运行 **注册表编辑器** （Regedt32.exe）。
7. 在HKEY\_LOCAL\_MACHINE子树中，转到以下键：  
   `SYSTEM\CurrentControlSet\Services\LanmanServer\Shares`。
8. 还原或导入注册表项。

   - 对于 Windows NT 和 Windows 2000，请单击注册表菜单上的“ **还原** ”。
   - 对于 Windows Server 2003，请单击“文件**”菜单上的**“**导入**”。
9. 键入步骤 3 和 4 中保存的文件的路径和文件名。

   注意

   此步骤将覆盖 Windows 计算机上已存在的共享，其中包含要还原的文件中存在的共享名称和权限。 在还原密钥之前，系统会提醒你注意此问题。
10. 重新启动服务器。

注意

完成此过程后，如果确定不应还原“共享”键，请重新启动计算机，然后按空格键以使用最后一个已知良好的配置。 还原共享密钥后，网络客户端可以使用共享。 如果在服务器上运行 net shares 命令，服务器将显示共享;但是，文件管理器不显示共享。 若要使文件管理器知道新还原的共享，请在服务器上创建任何新共享。 重启服务器或停止并重启服务器服务后，文件管理器将显示所有其他共享。

在 Windows NT 3.5 中，如果单击“文件管理器中的停止共享”，还原的共享仍显示，但它们灰显。

仅还原域用户的权限。 如果在以前的 Windows NT 安装中创建本地用户，该本地用户的唯一安全标识符 （SID） 将丢失。 保存和还原共享密钥时，文件夹和文件的 NTFS 权限不会受到影响。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/saving-restoring-existing-windows-shares)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
