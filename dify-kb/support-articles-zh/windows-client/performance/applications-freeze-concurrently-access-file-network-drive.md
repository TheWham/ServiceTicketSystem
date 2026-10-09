# 在 Windows 中，多个应用程序同时访问网络驱动器上的同一文件时发生冻结

本文针对"应用程序同时尝试访问 Windows 网络驱动器上的同一文件时发生冻结"的问题提供解决方法。

_适用于：_ &nbsp; Windows 10 - 所有版本  
_原始 KB 编号：_ &nbsp; 4039810

## 症状

考虑以下场景：

- 你在服务器上创建了一个共享文件夹，并向其中添加了文件。
- 在运行 Windows 10、Windows 8.1 或 Windows 7 的客户端上，将该共享文件夹挂载为网络驱动器。
- 你安装的第三方安全软件包含一个与某应用程序关联的文件系统微过滤器驱动程序（minifilter driver）。
- 该微过滤器同时附加到了保存 %SystemRoot% 路径的本地驱动器（例如 C 盘）和你创建的共享文件夹对应的网络驱动器上。
- 微过滤器通过 **FltSendMessage** 函数向应用程序发送一条包含网络驱动器上文件名的消息。
- 应用程序尝试使用收到的文件名打开该文件。
- 与此同时，同一台计算机上另一个与该微过滤器无关的应用程序也尝试打开网络驱动器上的同一个文件。

在这种情况下，两个应用程序都会冻结。

## 原因

此问题是由 Windows 客户端缓存驱动程序（Client-Side Caching Driver，Csc.sys）持有的资源锁导致的。当此问题发生时，Csc.sys 对某个文件获取了资源锁，然后请求其驱动程序堆栈上方的驱动程序打开该文件。这导致所有尝试访问该文件的应用程序都被迫等待，同时也使微过滤器的线程等待其关联的应用程序响应，形成死锁。

## 解决方法

如果此问题已经发生，请重启客户端。

为避免此问题，请使用"本地组策略编辑器"（gpedit.msc）禁用**脱机文件**（Offline Files）。具体做法是修改位于 **计算机配置\\管理模板\\网络\\脱机文件** 下的 **允许或禁止使用脱机文件功能** 组策略设置。

> **备注**
> 如果你必须使用**脱机文件**，则没有可用的解决方法。

## 状态

Microsoft 已确认这是本文开头所列 Microsoft 产品中存在的问题。

## 更多信息

在调用文件系统期间持有锁通常不是好的做法。原因记录在以下开发者博客文章中：  
[Issuing IO in minifilters: Part 1 - FltCreateFile](/archive/blogs/alexcarp/issuing-io-in-minifilters-part-1-fltcreatefile)

要识别如"症状"一节所述、附加到多个驱动器上的微过滤器，请在管理员命令提示符下运行以下命令：

```console
fltmc instances -v C:

fltmc instances -v \Device\Mup
```

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/applications-freeze-concurrently-access-file-network-drive)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
