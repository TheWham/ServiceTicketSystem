# 服务突然停止时显示错误 1058

本文提供了一个解决方案，用于解决服务突然停止时出现“错误 1058”的问题。

*适用于：* Windows 10 - 所有版本、Windows 7、Windows Vista、Windows XP  
*原始 KB 数：* 241584

## 现象

服务突然停止时，可能会收到以下错误消息：

> 错误 1058：服务无法启动，要么是因为它已禁用，要么是因为它没有与之关联的已启用设备。

尝试启动服务时，也可能会收到此错误消息。

## 原因

如果服务已禁用，或者当前正在使用的硬件配置文件已禁用该服务，则可能会出现此问题。

### Windows 10、Windows 7 和 Windows Vista 的解决方法

1. 单击“开始**”**，搜索*“服务*”，然后单击搜索结果中的“**服务**”。
2. 滚动直到找到服务，然后双击该服务。

   ![“路由和远程访问属性”对话框的“常规”选项卡下的“启动类型”选项的屏幕截图。](media/error-1058-displayed-when-service-stops/service-properties-win10.png)
3. 如果服务已禁用，请单击**“启动类型**”列表，然后选择“已禁用**”以外的**选项。
4. 单击“应用”。
5. 单击“开始**”**以尝试启动服务。
6. 单击“确定”。

### Windows XP 的分辨率

1. 单击“开始”，指向**“所有程序**”，指向**“管理工具**”，然后单击“**服务**”。
2. 滚动，直到找到已停止或禁用的服务。
3. 双击未启动的服务。
4. 单击**“登录”**选项卡。

   ![远程过程调用（RPC）定位符属性（本地计算机）对话框的“登录”选项卡的屏幕截图。](media/error-1058-displayed-when-service-stops/log-on-tab-shown.png)
5. 验证是否未为正在使用的硬件配置文件禁用该服务。 如果为硬件配置文件禁用了服务，请单击“ **启用**”。
6. **单击“常规**”选项卡，然后在**“启动类型**”框中，验证服务是否未禁用。 如果服务已禁用，请单击“自动**”**以在启动计算机时启动它。

   ![“常规”选项卡中启动类型框的屏幕截图。](media/error-1058-displayed-when-service-stops/verify-service-startup-type.png)
7. 单击“确定”。

## 详细信息

如果服务设置为自动启动，但已为正在使用的硬件配置文件禁用服务，则不会启动该服务，并且不会生成错误消息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/error-1058-displayed-when-service-stops)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
