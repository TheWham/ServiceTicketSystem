# 在 Windows 7 中尝试安装网络打印机时出现错误消息：0x0000052e

本文针对在 Windows 7 中尝试安装网络打印机时出现的错误 "0x0000052e" 提供解决方法。

_适用于：_ &nbsp; Windows 7 Service Pack 1  
_原始 KB 编号：_ &nbsp; 2269296

## 症状

当你尝试在运行 Windows 7 的计算机上安装网络打印机时，会收到以下错误消息：
> Windows 无法连接到打印机（详细信息：操作失败，错误为 0x0000052e）

## 原因

如果 Windows 7 客户端上的凭据与打印服务器上存储的凭据不匹配，就可能出现此问题。错误消息 "0x0000052e" 表示以下错误：
> 登录失败：用户名未知或密码错误。

## 解决方法

要解决此问题，请使用以下任一方法。

### 解决方法 1

在添加网络打印机之前，打开**命令提示符**窗口，并在**命令提示符**下键入以下内容：

```console
start \\<servername>\<printername>
```
> **备注**
> 在此命令中，\<servername> 表示打印服务器的名称，\<printername> 表示打印机的共享名。

在身份验证窗口中输入相应的凭据。

### 解决方法 2

在**凭据管理器**中存储受信任的凭据。为此，请按照下列步骤操作：

1. 在**控制面板**中，打开**凭据管理器**。
2. 单击**添加 Windows 凭据**。
3. 在对话框中输入相应的打印服务器名称，然后输入在打印服务器上受信任的用户名和密码。
4. 单击**确定**。

## 更多信息

此行为在更早的 Windows 版本中有所不同。在那些版本中，如果连接因用户名未知或密码错误而失败，系统会提示你输入凭据。

## 数据收集

如果需要 Microsoft 支持部门的帮助，建议你按照[使用 TSS 收集用户体验问题的信息](https://learn.microsoft.com/en-us/troubleshoot/windows-client/windows-troubleshooters/gather-information-using-tss-user-experience#printing)中提到的步骤收集信息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/error-message-0x0000052e-install-network-printer)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权，本文档为社区中文翻译）
