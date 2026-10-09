# 选择“授予用户对文档的独占权限”时，将用户的 Documents 文件夹重定向到其主目录失败

本文有助于修复以下问题：选择“授予用户对文档的独占权限”时，无法将用户的 Documents 文件夹重定向到其主目录。

*适用于：* Windows 7 Service Pack 1  
*原始 KB 数：* 2493506

## 现象

使用文件夹重定向策略将用户的文档文件夹重定向到其主目录，如果选择了“授予用户对文档的独占权限”，则无法创建同步合作关系，并且无法将文档数据复制到主目录。

应用程序事件日志中记录了以下错误：

> 日志名称: 应用程序  
> 源：Microsoft-Windows-Folder 重定向  
> 日期： <DateTime>  
> 事件 ID：502  
> 任务类别：无  
> 级别： 错误  
> 关键字：  
> 用户：`contoso.com\jim`  
> 计算机: `Win7-1.contoso.com`  
> 说明:  
> 未能将策略和重定向文件夹“Documents”应用于“\\`contoso.com`\home\jim\”。  
> 重定向选项=0x1211。  
> 发生以下错误：“无法创建文件夹”\\`contoso.com`\home\jim”。  
> 错误详细信息：“此安全 ID 可能未分配为此对象的所有者。

## 原因

1. 你有一台运行 Vista SP1 或 Windows 7 的计算机
2. 文件夹重定向策略配置为将 Documents 文件夹重定向到用户的主目录
3. “向用户授予对文档的独占权限”- 已启用
4. “还将重定向策略应用于 Windows 2000、Windows 200 Server、Windows XP 和 Windows Server 2003 操作系统” - 已禁用

在此配置中，不会创建同步伙伴关系，因此不会合并主目录中的文档和本地配置文件。

## 解决方法

执行下列操作之一：

1. 同时启用“授予用户对文档的独占权限”和“同时将重定向策略应用于 Windows 2000、Windows 200 Server、Windows XP 和 Windows Server 2003 操作系统”。 启用这两者后，成功创建同步伙伴关系，并在本地配置文件和主目录之间同步文档。

   -- 或 --
2. 禁用“授予用户对文档的独占权限”和“同时将重定向策略应用于 Windows 2000、Windows 200 Server、Windows XP 和 Windows Server 2003 操作系统”。 禁用两者后，成功创建同步伙伴关系，并在本地配置文件和主目录之间同步文档。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/redirect-users-documents-folder-to-their-home-directory-fail)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
