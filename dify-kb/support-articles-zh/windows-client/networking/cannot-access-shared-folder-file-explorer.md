# 无法在 Windows 10 中通过文件资源管理器访问共享文件夹

_适用于：_ &nbsp; Windows 10

## 常规排查

- 不使用**文件资源管理器**，改用**命令提示符**通过以下命令访问共享文件夹：

    ```console
    net use <DeviceName>: \\<ServerName>\<ShareName>
    ```
> **备注**
    > 有关更多信息，请参阅 [Net use](/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/gg651155(v=ws.11))。

- 按以下步骤在**控制面板**中启用 SMB 1.0 支持功能：
    1. 打开**控制面板**。
    2. 选择**程序** > **程序和功能** > **启用或关闭 Windows 功能** > **SMB 1.0/CIFS 文件共享支持**。
    3. 勾选 **SMB 1.0/CIFS 客户端**，然后按 Enter。

- 按以下步骤启用网络发现以及文件和打印机共享选项：
    1. 打开**控制面板**。
    2. 选择**网络和 Internet** > **网络和共享中心** > **高级共享设置**。
    3. 选择**启用网络发现**。
    4. 在**专用**下选择**启用文件和打印机共享**。
    5. 选择**保存更改**。

- 将指定服务的启动类型设置为**自动**，使计算机在网络上可见。操作步骤如下：
    1. 转到"开始"。
    2. 进入搜索，输入 *Services* 并按 Enter。
    3. 将以下服务的**启动类型**属性改为**自动**。
       - **Function Discovery Provider Host**
       - **Function Discovery Resource Publication**
       - **SSDP Discovery**
       - **UPnP Device Host**
    4. 重启系统。

你可能会收到以下错误消息：

## 你没有权限访问 \\\<IP 地址或主机名>

### 解决方案

1. 按以下步骤为要共享的文件夹向 **Everyone** 授予共享权限：
    1. 长按（或右键单击）共享文件夹。
    2. 选择**属性**，然后在**共享**选项卡上选择**高级共享**。
    3. 选择**权限**，勾选 **Everyone** 的**完全控制**为**允许**，然后按 Enter。
    4. 在**高级共享**对话框中选择**确定**。

2. 按以下步骤向 **Everyone** 授予**完全控制**权限：
    1. 在**安全**选项卡上选择**编辑**。
    2. 选择**添加**，在**输入要选择的对象名称**字段中输入 *Everyone*，然后按 Enter。
    3. 勾选 **Everyone** 的**完全控制**为**允许**，然后按 Enter。
    4. 关闭**属性**对话框。

3. 按以下步骤确认 TCP/IP NetBIOS 已启用：
    1. 转到"开始"。
    2. 进入搜索，输入 *Services* 并按 Enter。
    3. 在右窗格中双击 **TCP/IP NetBIOS Helper**，确认**启动类型**属性设置为**自动**。
    4. 转到**控制面板** > **网络和 Internet** > **网络和共享中心**，在左窗格中选择**更改适配器设置**，然后双击**以太网**。
    5. 选择**属性**，在**网络**选项卡上双击 **Internet 协议版本 4（TCP/IPv4）**。
    6. 选择**高级**，在 **WINS** 选项卡上选择**启用 TCP/IP 上的 NetBIOS**，然后按 Enter。
    7. 选择**确定**两次以关闭对话框。

## 你无法访问此共享文件夹，因为你组织的安全策略阻止未经身份验证的来宾访问

### 解决方案

你可以使用以下方法之一在计算机上启用来宾访问：

**方法 1**：使用**注册表编辑器**启用不安全的来宾登录

1. 打开**注册表编辑器**。
2. 转到 `Computer\HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\LanmanWorkstation`。
> **备注**
    > 如果该项不存在，则需要创建。长按（右键单击）**Windows**，选择**新建** > **项**，然后将该项命名为 *LanmanWorkstation*。

3. 长按（右键单击）**LanmanWorkstation**，选择**新建** > **DWORD（32 位）值**，然后将其命名为 *AllowInsecureGuestAuth*。双击它，将**数值数据**设置为 *1*，然后按 Enter。

**方法 2**：使用**本地组策略编辑器**启用不安全的来宾登录

1. 转到"开始"。
2. 进入搜索，输入 *gpedit.msc*，然后按 Enter。
3. 转到**计算机配置** > **管理模板** > **网络** > **Lanman Workstation**。
4. 在右侧窗格中，双击**启用不安全的来宾登录**。
5. 选择**已启用**，然后按 Enter。

## 错误代码：0x80004005。未指定的错误

不自动获取 IP 地址，改为手动指定 IP 地址。请按以下说明操作：

1. 如果想要为网络适配器指定 IP 地址，请选择**使用下面的 IP 地址**。
2. 在 **IP 地址**框中，键入要分配给此网络适配器的 IP 地址。该 IP 地址必须是网络可用地址范围内的唯一地址。请联系网络管理员获取网络的有效 IP 地址列表。
3. 在**子网掩码**框中，键入网络的子网掩码。
4. 在**默认网关**框中，键入网络上用于将你的网络连接到其他网络或 Internet 的计算机或设备的 IP 地址。
5. 在**首选 DNS 服务器**框中，键入将主机名解析为 IP 地址的计算机的 IP 地址。
6. 在**备用 DNS 服务器**框中，键入当首选 DNS 服务器不可用时想要使用的 DNS 计算机的 IP 地址。
7. 选择**确定**。在**本地连接 属性**对话框中，选择**关闭**。
8. 在**本地连接 状态**对话框中，选择**关闭**。

## 发生系统错误 53。找不到网络路径

当你尝试访问服务器消息块（SMB）文件共享时，会收到以下错误消息：
> 发生系统错误 53。找不到网络路径。

在网络跟踪中，服务器未发送连接建立请求（TCP SYN 数据包）。但是，你可以使用 [telnet](/windows-server/administration/windows-commands/telnet) 通过 TCP 端口 445 连接到服务器。

如果 **TCP/IP NetBIOS Helper** 服务已停止，或者该服务以 **Local System** 而非 **Local Service** 身份运行，就会出现此问题。

要解决此问题，请确保 **TCP/IP NetBIOS Helper** 服务以 **Local Service** 身份运行。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/cannot-access-shared-folder-file-explorer)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
