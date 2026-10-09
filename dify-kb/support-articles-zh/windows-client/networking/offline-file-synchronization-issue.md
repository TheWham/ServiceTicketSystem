# 脱机文件同步时间 - 在 Windows 7 中，“脱机/工作联机”选项按钮在脱机/联机转换后从 Windows 资源管理器中消失，客户端缓存将保持脱机状态，直到下次重启计算机

本文提供了一个解决方案，用于解决脱机/工作联机选项按钮在脱机/联机转换后从 Windows 资源管理器中消失的问题，客户端缓存将保持脱机状态，直到下次重启计算机。

*适用于：* Windows 7 Service Pack 1  
*原始 KB 数：* 2512089

## 现象

你已将 Windows 7 配置为脱机文件同步，以同步网络共享中的内容，并使其脱机可用。 用户注意到 Windows 7 通常更改为脱机模式;但是，当网络可用后，Windows 7 不会自动切换回联机模式。 无法同步 UNC 路径，并且同步中心没有可用于脱机文件同步伙伴关系的信息。

如果用户在 Windows 资源管理器中访问网络资源，则某些网络资源处于联机状态且可访问;但是，当用户尝试访问已脱机提供的资源时，将从客户端缓存显示脱机内容。 用户可以创建新文件并更改现有文件，但这些文件仍保留在本地缓存中。

为每个用户提供文件共享和子文件夹，如以下示例所示：

\\ServerName\ShareName$\dir1\dir2

具有相应权限的用户可以访问子文件夹 dir1 和 dir2，但无权查看共享 ShareName$的内容。

## 原因

此行为是由 Windows Vista 和 Windows 7 处理远程文件操作的方式引起的。 已分析 UNC 路径，并检查每个部件的可用性。 在上述部分中所述的情况下，Windows Vista 或 Windows 7 会检查前缀 \\ServerName。 如果成功，它会检查 \\ShareName$\ 是否可用。 由于此级别缺少访问权限，远程文件操作会失败，如果 UNC 路径脱机，客户端缓存 （CSC） 会提供脱机内容中的文件。

注意

如果使用 DFS 命名空间（AD 集成或独立），\\domain\folder1\folder2 CSC 也会检查 DFS 命名空间服务器上的 folder1 和 folder2。

## 解决方法

若要通过脱机文件同步解决此问题，请确保用户可以访问 UNC 路径的所有部分。 在 \\ServerName\ShareName$\dir1\dir2（其中 ServerName 可以是文件服务器或 DFSN 服务器）的 UNC 路径上，当用户同步子文件夹 dir1 时，ShareName$ 需要以下权限：

脱机文件的共享级别 （SMB） 权限共享 ShareName$：

| 用户帐户 | 默认权限 | 所需的最低权限 |
| --- | --- | --- |
| 所有人 | 读取 | 无权限 |
| 需要将数据置于共享上的用户组。 | 空值 | 更改 |

在此示例中，将从共享权限中删除“每个人”，并使用包含用户帐户的全局组来设置共享级别权限。

用于脱机文件同步的根文件夹 ShareName$ 所需的 NTFS 权限：

| 用户帐户 | 所需的最低权限 |
| --- | --- |
| Creator Owner | 仅完全控制、子文件夹和文件 |
| 管理员 | 无 |
| 需要将数据置于共享上的用户组 | 列出文件夹/读取数据 - 此文件夹、子文件夹和文件 |
| 所有人 | 无权限 |
| Local System | 完全控制、此文件夹、子文件夹和文件 |

在子文件夹 \dir1 和 \dir2 上，需要以下权限：文件夹 dir1 和 dir2 所需的 NTFS 权限才能进行脱机文件同步：

| 用户帐户 | 默认权限 | 所需的最低权限 |
| --- | --- | --- |
| %Username% | 空值 | 读取和写入 |
| Local System | 完全控制 | 完全控制 |
| 管理员 | 无权限 | 无权限 |
| 所有人 | 无权限 | 无权限 |

## 详细信息

在 Windows Vista 和 Windows 7 中，所有远程文件系统访问请求都由多个 UNC 提供程序（MUP）进行通道。 MUP 将请求重定向到能够处理远程文件系统请求的网络重定向程序（UNC 提供程序）。 例如，对于 SMB 请求，MUP 会将请求重定向到网络提供商 LanmanWorkstation （ntlanman.dll）。 LanmanWorkstation 调用调用网络重定向程序（mrxsmb.sys）的工作站服务（svchost.exe）。

MUP 对注册到 MUP 且能够用于请求类型的网络重定向程序执行前缀解析操作（IOCTL\_REDIR\_QUERY\_PATH） 请求。 此前缀解析操作分析 UNC 路径，并检查每个部件的可用性。 如果前缀解析中的返回消息STATUS\_LOGON\_FAILURE或STATUS\_ACCESS\_DENIED，则请求失败，MUP 将 UNC 路径声明为不可访问。

客户端缓存会截获流向网络重定向程序的请求。 如果前缀解析操作失败（如上一节中所述），CSC 会提供本地缓存中的内容（如果 UNC 路径之前已脱机提供）。

此行为在以下链接中进行了详细概述：

- [支持 UNC 命名和 MUP](https://msdn.microsoft.com/library/ff556761(v=vs.85).aspx)
- [IOCTL\_REDIR\_QUERY\_PATH IOCTL](https://msdn.microsoft.com/library/ff548313(v=vs.85).aspx)
- [网络重定向程序的基本体系结构](https://msdn.microsoft.com/library/ff538979(v=vs.85).aspx)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/offline-file-synchronization-issue)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
