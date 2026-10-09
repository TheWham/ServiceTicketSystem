# 尝试通过 HTTPS 添加 IPP 打印机时，会收到错误

本文提供了在尝试通过 HTTPS 添加 IPP 打印机时发生的错误的解决方案。

*适用于：* Windows 7 Service Pack 1  
*原始 KB 数：* 2021626

## 现象

尝试通过 HTTPS 将 IPP 打印机添加到 Windows Vista 或 Windows 7 工作站时，队列可能无法安装并出现以下错误：

> 添加打印机  
> 连接到打印机  
> Windows 无法连接到打印机。 检查打印机名称，然后重试。 如果这是网络打印机，请确保打印机处于打开状态，并且打印机地址正确。

## 原因

出现此问题的原因是 Windows 不信任或无法验证打印服务器正在使用的 SSL 证书，或者打印服务器正在使用自签名证书。

## 解决方法

这可以通过以下任一方法解决：

- 将打印服务器配置为使用来自工作站信任的外部证书颁发机构的有效 SSL 证书。
- 如果打印服务器和工作站都位于同一域中，请配置打印服务器以使用企业证书颁发机构的有效 SSL 证书。
- 如果打印服务器使用的是自签名证书，请在工作站上安装自签名证书。

### 如何在 Windows 客户端上安装 IPP 打印服务器的自签名证书

如果打印服务器使用的是自签名证书，则可以使用以下步骤在客户端上安装自签名证书，以便它们能够使用打印机。

注意

这只能针对你信任的服务器中的 SSL 证书执行。

1. 以管理员身份登录到客户端
2. 在“开始”菜单中查找 Internet Explorer，右键单击它，然后单击“ **以管理员**身份运行”。
3. 在 Internet Explorer 中，使用 HTTPS 浏览到打印服务器（例如 `https://PrintServerName/`）
4. 在地址栏中，“证书错误”一词应显示在红色盾牌图标旁边的右侧 - 单击错误。
5. 单击“ **查看证书**”。
6. 在证书窗口中，单击“ **安装证书...”**。
7. 选择“将所有的证书放入下列存储”。
8. 单击“ **浏览...”**。
9. 选择 **“受信任的根证书颁发机构** ”，然后单击“ **确定**”。
10. 单击“下一步**”**，然后单击“**完成**”。
11. 将显示安全警告，指出要从无法验证的源添加证书。 单击“是**”**信任此 SSL 证书。
12. 关闭 Internet Explorer。
13. 现在可以安装打印机。

## 数据收集

如果需要Microsoft支持方面的帮助，建议按照使用 TSS 收集信息中的 [步骤收集用户体验问题](../windows-troubleshooters/gather-information-using-tss-user-experience#printing)来收集信息。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/error-occurs-when-adding-ipp-printer)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
