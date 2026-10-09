# 连接到工作组计算机上的无线网络时出现Windows 安全警报

本文可帮助修复连接到工作组计算机上的无线网络时出现Windows 安全警报的问题。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 2518158

## 现象

在连接到属于工作组的 Windows 系统上的无线网络时，可能会显示类似于以下内容的Windows 安全警报对话框：

> 服务器 `<Authentication server>` 提供了由 `<CA name>`此配置文件颁发的有效证书，但 `<CA name>` 未配置为此配置文件的有效信任定位点。 此外，服务器 `<Authentication server>` 未配置为有效的 NPS 服务器以连接到此配置文件。

或

> 服务器 `<Authentication server>` 提供了由 `<CA name>`此配置文件颁发的有效证书，但 `<CA name>` 未配置为此配置文件的有效信任定位点。

如果单击对话框中的“连接”按钮，将成功建立无线连接。

## 原因

若要验证服务器证书，Windows 将检查链中的第二个元素（颁发最终证书的证书颁发机构（CA）是否为 Windows NT 身份验证的受信任 CA。 如果 CA 存在于存储在存储位置的系统 `NTAuth` 注册表存储 `CERT_SYSTEM_STORE_LOCAL_MACHINE_ENTERPRISE` 中，则将其视为受信任。 如果此验证失败，可能会出现“症状”部分中的任一警告消息。 默认情况下，CA 证书不在属于工作组的 Windows 系统上的 NTAuth 存储中。

## 解决方法

若要解决此问题，可以将颁发证书的 CA 的证书导出到身份验证服务器到文件。 将文件复制到工作组计算机，然后从提升的命令提示符运行以下命令：

`certutil -enterprise -addstore NTAuth CA_CertFilename.cer`

## 详细信息

有关如何将第三方证书颁发机构 （CA） 证书导入企业 NTAuth 存储，请参阅 <https://support.microsoft.com/kb/295663>

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/windows-security-alert-wireless-network)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
