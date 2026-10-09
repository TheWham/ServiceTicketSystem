# 如何在 Windows 中配置 CacheLocation 注册表值来更改 CSC 文件夹的位置

本文介绍如何通过配置 CacheLocation 注册表值来更改客户端缓存 （CSC） 文件夹的位置。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 937475

## 简介

不能使用 Cachemov.exe 工具在 Windows Vista 中移动客户端缓存 （CSC） 文件夹。 但是，可以通过配置 CacheLocation 注册表值来更改 CSC 文件夹的位置。

注意

CSC 文件夹是 Windows 在其中存储脱机文件的文件夹。

## 详细信息

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 但是，注册表修改不当可能会出现严重问题。 因此，按以下步骤操作时请务必谨慎。 作为额外保护措施，请在修改注册表之前先将其备份。 如果之后出现问题，您就可以还原注册表。 有关如何备份和还原注册表的详细信息，请单击以下文章编号以查看Microsoft知识库中的文章： [322756](https://support.microsoft.com/help/322756) 如何在 Windows 中备份和还原注册表

若要更改 CSC 文件夹的位置，请执行以下步骤。

注意

Windows Vista 中只有一个缓存文件夹。 因此，无需为其他用户重复这些步骤。

1. 单击“开始”**，在“搜索**”框中键入 regedit**，然后按 Enter。******
2. 找到以下注册表子项，然后右键单击它：  
   `HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\CSC`
3. 指向“新建**”**，然后单击“**键**”。
4. 在新键的名称框中键入参数。
5. 右键单击 **“参数”** 键，指向 **“新建**”，然后单击“ **字符串值**”。
6. 若要命名新值，请键入 CacheLocation，然后按 Enter。
7. 右键单击 **CacheLocation**，然后单击“ **修改**”。
8. 在 **“值”数据** 框中，键入要在其中创建缓存的新文件夹的名称。

   注意

   对文件夹名称使用 Microsoft Windows NT 格式。

   例如，如果希望缓存位置为 *d：\csc*，请键入以下内容： *\？？\d：\csc*
9. 退出注册表编辑器，然后重启计算机。

注意

网络管理员可以在计算机位于网络之前或此值提供给最终用户之前设置此值。 在这种情况下，不会将内容置于默认位置。 此外，还可以使用脚本设置 CSC 文件夹的位置。

本文档中的信息和解决方案表示截至发布日期Microsoft公司的当前视图。 此解决方案通过 Microsoft 或第三方供应商提供。 Microsoft不特别推荐本文可能介绍的任何第三方提供商或第三方解决方案。 本文可能还有其他第三方提供商或第三方解决方案未介绍。 由于Microsoft必须响应不断变化的市场状况，因此不应将此信息解释为Microsoft的承诺。 Microsoft 不担保或认可由 Microsoft 或提到的任何第三方供应商提供的任何信息或任何解决方案的准确性。

Microsoft 不作任何担保，并拒绝所有明示、暗示或法定的表述、担保和条件。 这些内容包括但不限于有关任何服务、解决方案、产品或任何其他材料或信息的陈述、担保或标题条件、不侵权、令人满意的条件、适销性和适用性。 在任何情况下，对于本文中提到的任何第三方解决方案，Microsoft 概不负责。  
有关如何在 Windows Vista 中移动脱机文件缓存的详细信息，请访问以下网站： [Microsoft存储](https://techcommunity.microsoft.com/t5/storage-at-microsoft/bg-p/FileCAB)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/change-csc-folder-location-with-cachelocation-registry)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
