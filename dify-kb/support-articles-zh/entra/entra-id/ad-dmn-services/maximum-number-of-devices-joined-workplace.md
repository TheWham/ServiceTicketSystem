# 错误（在工作区加入期间，已达到用户可加入工作区的最大设备数）

本文介绍尝试执行工作区加入操作时出现“用户可加入工作区的最大设备数”错误的问题。

*原始产品版本：*Windows Server 2012 R2 Datacenter、Windows Server 2012 R2 Standard、Windows 8.1 企业版、Microsoft Entra ID  
*原始 KB 数：* 3045379

## 现象

当用户尝试在 WIndows 设备上执行工作区加入操作时，他们会收到以下消息：

> 确认你使用的是当前登录信息，并且工作区使用此功能。 此外，与工作场所的连接现在可能不起作用。 请稍候，然后重试。

此外，管理员可能会在事件查看器中看到以下事件详细信息。

> 事件 ID：200  
> 日志名称：Microsoft-Windows-Workplace Join/Admin Source：Microsoft-Windows-Workplace Join 级别：错误说明：已达到用户可加入工作区的最大设备数。  
> 注册服务 URI： `https://enterpriseregistration.windows.net/EnrollmentServer/DeviceEnrollmentWebService.svc`

## 原因

出现此问题的原因是用户已加入最大设备数，并且已满足指定的配额。

## 解决方法

若要解决此问题，请检查配额配置。 然后，检查用户以前注册的设备数。 如果达到配额，请按照以下步骤操作，具体取决于适用的方案。

- 如果用户尝试执行 Workplace Join 以Microsoft Entra ID
  1. 删除用户的设备。
     1. 以公司管理员身份从Microsoft 365 管理中心登录到Azure 门户或启动 Microsoft Entra ID 控制台。
     2. 移动到用户尝试加入的目录。
     3. 找到 **“用户**”，然后找到无法执行 Workplace Join 操作的用户。
     4. 找到 **设备**。
     5. 查看列表以确定可删除哪些设备。 然后单击“ **删除设备**”。
  2. 增加已注册的设备配额。
     1. 以公司管理员身份从Microsoft 365 管理中心登录到Azure 门户或启动 Microsoft Entra ID 控制台。
     2. 移动到用户尝试加入的目录。
     3. 找到 **“设备”**，然后找到 **“设备设置**”。
     4. 将 **每个用户** 设置的最大设备数更改为更大的值。
- 如果用户正在尝试执行 Workplace Join 到本地 Active Directory 站点
  1. 删除用户的设备。
     - 使用 Windows PowerShell 脚本识别设备和删除与用户关联的设备。
  2. 增加已注册 **的设备配额** 值。
     1. 登录到 AD FS 服务器。
     2. 以提升的管理员身份运行 Windows PowerShell。
     3. 运行以下命令以增加配额：

        ```
        Set-ADFSDeviceRegistration -DevicesPerUser [0 - 1000]
        ```

        例如，运行以下命令，将用户的设备数设置为 10：

        ```
         Set-ADFSDeviceRegistration -DevicesPerUser 10
        ```

还可以通过查看 DRS 事件日志来验证用户是否已达到设备容量。

1. 在 DRS 服务器上打开事件查看器。
2. 浏览到位置： `Applications and Services Logs\Device Registration Service\DRS\Admin`
3. 查找事件 ID 125。 它应如下所示：

   > 用户“user@domain.com ： GUID”不符合注册类型为“device\_type”原因“DeviceCapReached”的设备的条件。

## 详细信息

有关故障排除的详细信息，请参阅 [诊断日志记录，以排查工作区加入问题](https://support.microsoft.com/help/3045377)。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/maximum-number-of-devices-joined-workplace)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
