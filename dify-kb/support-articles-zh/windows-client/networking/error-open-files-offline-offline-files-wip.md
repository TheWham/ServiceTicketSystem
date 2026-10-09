# 使用脱机文件和 Windows 信息保护时无法脱机打开文件

本文提供了一种解决方法，用于防止你在将脱机文件功能与 Windows 信息保护一起使用时脱机打开文件。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 3187045

## 现象

假设出现了下面这种情景：

- 已安装 Windows 10。
- 特殊文件夹（例如，文档或收藏夹）重定向到文件共享。
- 重定向文件夹中的用户数据通过脱机文件功能在本地缓存。
- 系统上启用了 Windows 信息保护（也称为企业数据保护）。
- 你正在使用由 Windows 信息保护管理的应用程序。

如果尝试在此方案中脱机工作时尝试打开文件，则尝试会失败。 在这种情况下显示的错误消息因应用程序而异。 Word 和 Excel 失败并出现以下错误：

> 很抱歉，无法打开“\\severname\fileshare\filename”

## 原因

出现此问题的原因是脱机文件功能不支持 Windows 信息保护。

## 解决方法

若要解决此问题，请使用以下某种方法：

- 使用不受 Windows 信息保护管理的应用程序打开该文件。
- 联机工作时打开该文件（已连接到公司网络）。

## 详细信息

没有计划更新脱机文件以支持 Windows 信息保护。 建议迁移到新式文件同步解决方案，例如 [工作文件夹](https://technet.microsoft.com/library/dn265974.aspx) 或 [OneDrive for Business](https://onedrive.live.com/about/business/)。

有关如何从脱机文件迁移到工作文件夹的信息，请参阅以下 TechNet 站点：

[工作文件夹脱机文件 (CSC) 迁移指南](https://blogs.technet.microsoft.com/filecab/2016/08/12/offline-files-csc-to-work-folders-migration-guide/)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/error-open-files-offline-offline-files-wip)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
