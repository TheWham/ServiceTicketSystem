# 重定向到映射的驱动器号而不是 UNC 路径时，文件夹重定向无法应用

本文修复了重定向到映射驱动器号而不是 UNC 路径时文件夹重定向无法应用的问题。

*适用于：* Windows 7 Service Pack 1  
*原始 KB 数：* 2859465

## 现象

假设出现了下面这种情景：

- 为用户配置主驱动器（例如：H：）。
- 使用“重定向到以下位置”将文件夹重定向到主驱动器，并指定驱动器号（例如：H：\Documents），而不是使用 UNC 路径。
- 用户是管理员。

在此方案中，文件夹重定向无法应用，并记录以下事件：

> 日志名称: 应用程序
>
> 源：Microsoft-Windows-Folder 重定向
>
> 日期： <DateTime>
>
> 事件 ID：502
>
> 任务类别：无
>
> 级别： 错误
>
> 关键字：
>
> 用户：Contoso\raj
>
> 计算机: `TestPC.Contoso.com`
>
> 说明:
>
> 无法将策略和重定向文件夹“Documents”应用到“H：\Documents”。
>
> 重定向选项=0x1001。
>
> 出现以下错误：“无法创建文件夹”H：\Documents”。
>
> 错误详细信息：“系统找不到指定的路径。

## 原因

当管理员登录到 Windows 时，本地安全机构（LSA）会创建两个访问令牌。 如果 LSA 通知用户是管理员组的成员，则 LSA 将创建第二个登录，该登录名删除了管理员权限（已筛选）。 由于 LSA 在两个单独的登录会话期间创建了访问令牌，因此访问令牌包含单独的登录 ID。 标准用户访问令牌用于映射驱动器。

应用策略时，它使用最高的令牌（管理令牌），因此它看不到映射驱动器。

## 解决方法

始终建议在重定向文件夹时使用 UNC 路径，而不是驱动器映射号。

若要解决此问题，请使用 UNC 路径而不是使用地图驱动器号重定向文件夹。 如果要将文件夹重定向到主驱动器，可以使用“重定向到用户的主目录”选项。

## 解决方法

若要解决此问题，请使用以下某种方法：

- 使用“EnableLinkedConnections”注册表。 此值允许 Windows 在已筛选的访问令牌与 Administrators 组成员的完整管理员访问令牌之间共享网络连接。 配置此注册表值后，LSA 会检查是否有另一个访问令牌与当前用户会话关联（如果网络资源映射到访问令牌）。 如果 LSA 确定存在链接访问令牌，则会将网络共享添加到链接位置。

  若要配置 EnableLinkedConnections 注册表值，请执行以下步骤：

  1. 单击“开始”**，在“开始搜索**”框中键入 regedit*，然后按 Enter。*****
  2. 找到并右键单击以下注册表子项： `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System`
  3. 指向 **“新建**”，然后单击 **“DWORD 值**”。
  4. 键入 *EnableLinkedConnections*，然后按 Enter。
  5. 右键单击 **EnableLinkedConnections**，然后单击“ **修改**”。
  6. 在“**数值数据**”框中，键入 *1*，然后单击“**确定**”。
  7. 退出注册表编辑器，然后重启计算机。

  重要

  此解决方法可能会使系统不安全。 Microsoft不支持此解决方法。 如果使用此解决方法，需自行承担风险。
- 禁用 UAC。 禁用 UAC 会停止拆分令牌，但不建议禁用 UAC。

  [在 Windows Server 上禁用用户帐户控制（UAC）](https://support.microsoft.com/help/2526083)

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/cannot-redirect-folder-use-drive-map-letter)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
