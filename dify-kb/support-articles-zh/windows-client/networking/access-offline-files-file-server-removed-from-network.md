# 文件服务器已从网络中移除后，仍可访问脱机文件（基于 Windows 7 的客户端计算机）

本文介绍一个问题：即使文件服务器已从网络中移除，你仍可访问脱机文件。

_适用于：_ &nbsp; Windows 7 Service Pack 1  
_原始 KB 编号：_ &nbsp; 942974

## 症状

在基于 Windows Vista 或 Windows 7 的客户端计算机上，即使文件服务器已从网络中移除，你仍可访问脱机文件。此外，你还可以在控制面板的**脱机文件**项中删除脱机文件和临时文件。

## 解决方案
> **重要**
> 本节、方法或任务包含的步骤会告诉你如何修改注册表。但是，如果修改注册表不当，可能会出现严重问题。因此，请务必仔细按照这些步骤操作。为了加强保护，请先备份注册表再进行修改。这样，如果出现问题，你可以还原注册表。有关如何备份和还原注册表的更多信息，请单击以下文章编号以查看 Microsoft 知识库中相应的文章：  
[322756](https://support.microsoft.com/help/322756) 如何在 Windows 中备份和还原注册表

要解决此问题，请重新初始化脱机文件缓存。为此，请按照下列步骤操作：

1. 单击**开始**，在**开始搜索**框中键入 *regedit*，然后按 Enter。
> **备注**
    > 如果系统提示你输入管理员密码或进行确认，请键入密码或单击**继续**。
2. 找到以下注册表子项，然后右键单击它：

    `HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\CSC`
3. 指向**新建**，然后单击**项**。
4. 在框中键入 *Parameters*。
5. 右键单击 **Parameters**，指向**新建**，然后单击 **DWORD（32 位）值**。
6. 键入 *FormatDatabase*，然后按 Enter。
7. 右键单击 **FormatDatabase**，然后单击**修改**。
8. 在**数值数据**框中键入 *1*，然后单击**确定**。
9. 退出注册表编辑器，然后重新启动计算机。
> **备注**
> 在添加此注册表项之前，请确保文件已同步。否则，未同步的更改将丢失。

你也可以使用 Reg.exe 命令行工具自动完成此注册表值的设置。为此，请在管理员命令提示符下运行以下命令：

```console
REG ADD "HKLM\System\CurrentControlSet\Services\CSC\Parameters" /v FormatDatabase /t REG_DWORD /d 1 /f
```  
> **备注**
>
> - 在添加此注册表项之前，请确保文件已同步。否则，未同步的更改将丢失。
> - 新注册表项的实际值会被忽略。
> - 此注册表更改需要重新启动计算机。计算机重新启动时，Shell 将重新初始化 CSC 缓存，然后在该注册表项存在的情况下将其删除。

## 状态

Microsoft 已确认这是"适用于"部分中列出的 Microsoft 产品中的问题。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/access-offline-files-file-server-removed-from-network)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
