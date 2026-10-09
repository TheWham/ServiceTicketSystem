# 使用 FQDN 或 IP 地址时，Intranet 站点标识为 Internet 站点

本文为使用完全限定域名（FQDN）或 IP 地址时 Intranet 站点标识为 Internet 站点的问题提供了一种解决方法。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 303650

## 现象

使用 Internet 协议（IP）地址或 FQDN 访问局域网（LAN）、Intranet 共享或 Intranet 网站时，共享或网站可能标识为 Internet 区域而不是本地 Intranet 区域中。 例如，如果你使用Microsoft Internet Explorer 或 Windows Internet Explorer、Microsoft Windows Explorer、命令提示符或基于 Windows 的程序访问共享或网站，或者使用以下任一格式的地址时，可能会发生此行为：

- `\\Computer.childdomain.domain.com\Share`
- `http://computer.childdomain.domain.com`
- `\\157.54.100.101\share`
- `file://157.54.100.101/share`
- `http://157.54.100.101`

无论配置了以下任何设置还是所有设置，都可能发生此行为：

- 在 Microsoft Internet Explorer 或 Windows Internet Explorer 中，你已将 FQDN （或 \*.domain.com） 或 IP 地址（或地址范围）添加到**“不使用代理服务器”作为地址，以**“代理设置”对话框中的“例外**”**部分**下的**框开头。

  注意

  **若要在 Internet Explorer 中找到“代理设置”**对话框，请单击“工具**”**，单击“**Internet 选项**”，单击“**连接**”，然后单击“**代理设置”。**
- 已选中 **“本地地址** 旁路代理服务器”复选框，该复选框位于 **“局域网”（LAN）“设置** ”对话框中。

  注意

  若要在 **Internet Explorer 中找到“局域网”（LAN）设置** 对话框，请单击“ **工具**”，单击“ **Internet 选项**”，单击“ **连接**”，然后单击“ **局域网”（LAN）设置**。
- 已选中“**包括绕过代理服务器**的所有站点”，并在**“本地 Intranet**”对话框中选中“包括所有网络路径”（UNC）**复选框**。

  **若要在 Internet Explorer 中找到“本地 Intranet**”对话框，请单击“工具**”**，单击“**Internet 选项**”，单击“**安全性**”，然后单击“**本地 Intranet**”。

此行为可能导致 Internet Explorer 在访问需要身份验证的 Intranet 网站时提示输入凭据。 或者，在使用 Internet Explorer 安全管理器确定文件是否位于受信任的安全区域中的程序中，可能会提示或阻止打开 Intranet 网站上的文件或通用命名约定（UNC）。 例如，尝试使用 Access 2002 打开本地 Intranet 共享（使用 FQDN 或 IP 地址）上的 Access 数据库（.mdb）文件时，可能会收到以下错误消息：

> Microsoft Access 无法打开此文件。  
> 此文件位于 Intranet 外部或不受信任的站点上。 Microsoft Access 由于潜在的安全问题，Access 无法打开该文件。  
> 若要打开该文件，请将其复制到计算机或可访问的网络位置。

注意

Windows Server 2003 包含名为 Internet Explorer 增强安全配置的新可选组件。 此组件将所有 Intranet 网站和未显式列出在本地 Intranet 区域中的所有 UNC 路径分配给 Internet 区域。 默认情况下，Internet 区域使用高安全级别。 因此，使用 NetBIOS 名称访问 Intranet 网站和 UNC 路径时，可能会遇到这些症状。 例如，如果使用 `http://server` 或 \\server\share，或者使用 IP 地址或 FQDN 时，可能会遇到这些症状。

有关 Internet Explorer 增强的安全配置的详细信息，请参阅 [有关 Internet Explorer 增强安全配置（ESC）的](https://support.microsoft.com/help/4551931)常见问题解答。

## 原因

如果 FQDN 或 IP 地址包含句点，则可能会发生此行为。 如果 FQDN 或 IP 地址包含句点，Internet Explorer 会将网站或共享标识为 Internet 区域中。

## 解决方法

若要解决此问题，请将适当的 IP 地址范围或完全限定的域名（FQDN）添加到本地 Intranet。 或更改 Internet 区域的安全级别。 在用户身份验证选项上，从仅 Intranet 区域中的自动登录更改为使用当前用户名和密码自动登录。

如果使用 Internet Explorer 的增强安全配置和 Windows Server 2003，并且使用 NetBIOS 名称访问 Intranet 站点，请使用以下任一方法来解决此问题：

- 将站点添加到本地 Intranet 区域。 若要将站点添加到本地 Intranet 区域，请在 Internet Explorer 中打开站点，单击“文件”，指向“**添加此站点”**，单击“**本地 Intranet 区域**”，单击“本地 Intranet**”对话框中的“**添加****”，然后单击“**关闭**”。
- 将站点添加到受信任的站点区域。 若要将站点添加到受信任的站点区域，请在 Internet Explorer 中打开站点，单击“文件”**，指向“**添加此站点”**，单击“**受信任的站点”区域**，单击**“受信任的站点**”对话框中的“添加****”，然后单击“**关闭**”。**
- 关闭增强的安全配置。 必须是管理员才能关闭增强的安全配置。 可以关闭用户的增强安全配置（如受限用户和受限用户），并为管理员保留该配置。 若要关闭用户的增强安全配置，请打开**控制面板，单击“添加或删除程序**”，单击“添加/删除 Windows 组件**”，单击“Internet Explorer 增强的安全配置**”，单击**“详细信息**”，单击“用户**”，单击“确定****”**，单击“下一步**”，然后单击“完成**”**，然后重启 Internet Explorer 以应用新设置。**

管理员可以使用客户端设置或服务器设置将适当的 IP 地址范围或 FQDN 添加到本地 Intranet。 例如，管理员可以使用 TCP/IP 后缀、添加 \*.domain.com，或将相应的 IP 地址范围添加到 **客户端 Internet Explorer 中的本地 Intranet 站点** 区域。 在服务器上，管理员可以使用代理自动配置脚本。 以下解决方法将 \*.domain.com 或相应的 IP 地址范围添加到 Internet Explorer 中所有客户端计算机的本地 Intranet 站点区域。

### 用户

若要解决此问题，每个用户必须将 \*.domain.com 或相应的 IP 地址范围添加到 **“本地 Intranet 站点** ”对话框：

1. 在 Internet Explorer 中，单击“工具”，然后单击“Internet 选项”。
2. 在**“安全**”选项卡上，单击“本地 Intranet**”**，然后单击“**站点**”。
3. 单击“高级”**，然后在“将此网站添加到区域**”框中`domain.com`，键入 **.domain.com* 或 IP 地址范围（例如 157.54.100-200）。*****
4. 单击“**添加**”，单击“确定****”****，然后单击“确定”，然后再次单击“确定**”**关闭**“Internet 选项**”对话框。
5. 重新启动计算机。

### 管理员

重要

此部分（或称方法或任务）介绍了修改注册表的步骤。 但是，注册表修改不当可能会出现严重问题。 因此，按以下步骤操作时请务必谨慎。 作为额外保护措施，请在修改注册表之前先将其备份。 如果之后出现问题，您就可以还原注册表。 有关如何备份和还原注册表的详细信息，请参阅：[如何备份和还原 Windows 中的注册表](https://support.microsoft.com/help/322756)。

管理员可以通过对注册表进行以下更改来部署此设置：

1. 对于应包含在本地 Intranet 区域中的每个域，请在HKEY\_CURRENT\_USER**（仅限当前登录的用户）或HKEY\_LOCAL\_MACHINE**（对于本地计算机上的所有用户）**下**，将密钥添加到`domain.com`相应的注册表项中：

   - `Software\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap\Domains` （对于 32 位版本的 Internet Explorer 或 64 位版本的 Internet Explorer（如果已关闭增强的安全配置），则为 64 位版本的 Windows XP 或 Windows Server 2003。
   - `Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap\Domains` （对于 64 位版本的 Windows XP 或 64 位版本的 Windows Server 2003 上的 32 位版本的 Internet Explorer，如果已关闭增强的安全配置。）
   - `Software\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap\ESCDomains` （对于 32 位版本的 Windows Server 2003 上的 Internet Explorer，或 64 位版本的 Windows Server 2003 上的 64 位版本的 Internet Explorer（如果启用了增强的安全配置）。
   - `Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap\ESCDomains` （对于 64 位版本的 Windows Server 2003 上的 32 位版本的 Internet Explorer，如果启用了增强的安全配置。

   注意

   默认情况下，安全区域设置存储在HKEY\_CURRENT\_USER**注册表项中**。 由于此密钥是针对每个用户动态加载的，因此一个用户的设置不会影响另一个用户的设置。 如果 **安全区域：仅在组策略中启用计算机设置设置，或者以下键中的 Security\_HKLM\_only DWORD 值设置为 1，则仅使用本地计算机设置** ：  
   `HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\CurrentVersion\Internet Settings`  
   启用此策略设置后，将仅使用计算机设置，而不是用户设置。
2. 向键添加一个名为星号字符 = 的 `domain.com` DWORD 值，并将其设置为 1。
3. 对于必须包含在本地 Intranet 区域中的每个 IP 地址范围，请将 Range**x 键（其中 x** 为 1、2、3 等）添加到以下HKEY\_CURRENT\_USER下的注册表项（仅适用于当前登录的用户）或**HKEY\_LOCAL\_MACHINE**（对于本地计算机上的所有用户）：

   - `Software\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap\Ranges` （对于 32 位版本的 Internet Explorer 或 64 位版本的 Windows XP 或 Windows Server 2003 上的 64 位版本的 Internet Explorer。
   - `Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap\Ranges` （对于 64 位版本的 Windows XP 或 64 位版本的 Windows Server 2003 上的 32 位版本的 Internet Explorer。

   注意

   默认情况下，安全区域设置存储在HKEY\_CURRENT\_USER**注册表项中**。 由于此密钥是针对每个用户动态加载的，因此一个用户的设置不会影响另一个用户的设置。 如果 **安全区域：仅在组策略中启用计算机设置设置，或者以下键中的 Security\_HKLM\_only DWORD 值设置为 1，则仅使用本地计算机设置** ：  
   `HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\CurrentVersion\Internet Settings`  
   启用此策略设置后，仅使用计算机设置，而不是用户设置。
4. 向 Range**x** 键添加一个名为星号字符 = 的 DWORD 值，并将其设置为 1。
5. 将名为 *：Range 的字符串值（后跟字 Range* 的冒号字符）添加到 Range**x** 键，然后将其设置为 IP 地址范围（例如 157.54.100-200.\*）。

注意

管理员可以在 Active Directory 环境中部署设置。

有关如何执行此操作的详细信息，请参阅 [如何使用组策略对象](../../developer/browsers/administration/advanced-settings)在 Internet Explorer 中设置高级设置。

重要

此解决方法不适用于使用 IP 地址的 UNC 或 file:// 地址。 例如，Internet Explorer 将 \\157.54.100.101\share 或 file://157.54.100.101/share 标识为位于 Internet 区域中，即使将适当的 IP 地址范围添加到本地 Intranet 站点列表也是如此。 在这种情况下，必须使用具有 NetBIOS 名称（例如 **\\server\share**）的 file:// URL，以便在本地 Intranet 区域中标识站点。 此外，某些应用程序可能无法使用 http:// 地址打开文件，即使网站位于 LAN 上，也无法使用 NetBIOS 名称（例如 `http://server`）。 例如，Access 2002 无法从 http:// 地址打开文件。 如果尝试使用 IP 地址、FQDN 或 NetBIOS 名称在 Intranet 网站上打开 Access 数据库文件（.mdb），Access 2002 会错误地报告该文件在 Intranet 外部或不受信任的站点上，方法是在本文的“症状[”部分中显示错误消息](#symptoms)。

## Status

此行为是特意这样设计的。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/intranet-site-identified-as-an-internet-site)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
