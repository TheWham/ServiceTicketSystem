# 如果需要其他证书下载，使用 ADAL 从 Android 设备进行身份验证会失败

本文介绍需要其他证书下载时，来自 Android 设备的 Azure Active Directory 身份验证库 （ADAL） 身份验证失败的问题。

*原始产品版本：* Microsoft Entra ID  
*原始 KB 数：* 3203929

## 现象

尝试使用适用于 Android 的 ADAL 进行身份验证时，联合身份验证登录可能会失败。 具体而言，应用程序在尝试显示登录页时触发 AuthenticationException 错误。 在 Google Chrome 中，STS 登录页可能被称为不安全。 此问题仅在 Android 设备上发生，对于使用 ADAL for Android 连接到联合服务器的任何应用程序。

若要确定是否遇到此问题，请运行以下测试：

1. 获取安全令牌服务（STS）服务器的完全限定域名（FQDN）。 为此，请按照下列步骤进行操作：

   1. 转到 <https://login.microsoftonline.com> 非 Android 设备。
   2. 输入工作或学校帐户。
   3. 重定向到联合 STS 登录页时，请注意浏览器中的 URL 地址。 应类似于 `https://sts.contoso.com`。 FQDN 为 `sts.contoso.com`.
2. 转到以下 URL，将 <STS\_SERVER\_FQDN\_HERE> 替换为 STS FQDN：

   `https://www.ssllabs.com/ssltest/analyze.html?d=<STS_SERVER_FQDN_HERE>&hideResults=on&latest`

   例如：

   `https://www.ssllabs.com/ssltest/analyze.html?d=sts.contoso.com&hideResults=on&latest`
3. 查看是否显示以下任何消息：

   - 额外下载
   - 服务器发送
   - 在信任存储中

   如果任何 SSL 证书显示“额外下载”消息，则根据以下屏幕截图，你遇到了本部分中前面所述的问题：

   ![额外下载消息的屏幕截图。](media/adal-authenticate-android-devices-fail/extra-download-message.png)

   以下屏幕截图显示了带有“服务器发送”消息的证书，演示了 Android 设备上的身份验证成功：

   ![服务器消息发送的屏幕截图。](media/adal-authenticate-android-devices-fail/sent-by-server-message.png)

## 原因

Android 不支持从证书的 **authorityInformationAccess** 字段下载其他证书。 在所有 Android 版本和设备以及 Chrome 浏览器上都是如此。 如果整个证书链未从 Active Directory 联合身份验证服务（AD FS）传递，则标记为基于 **authorityInformationAccess** 字段进行额外下载的任何服务器身份验证证书都会触发此错误。

## 解决方法

若要解决此问题，请将 STS 和 Web 应用程序代理 （WAP） 服务器配置为连同 SSL 证书一起发送必要的中间证书。 为此，请按照下列步骤进行操作：

1. 将 SSL 证书从计算机导出到 AD FS 和 WAP 服务器（或服务器）的计算机的个人存储时，请确保导出私钥，并选择 **个人信息交换 - PKCS #12**。 此外，请确保在证书路径中包括所有证书（如果可能）和“导出所有扩展属性”复选框处于选中状态。
2. 在 Windows 服务器上运行 `certlm.msc` ，然后导入 \*。PFX 文件进入计算机的个人证书存储。 执行此操作时，当客户端应用程序使用 ADAL 进行身份验证时，服务器将传递整个证书链。

注意

还应更新网络负载均衡器的证书存储，以包含整个证书链。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/mfa/adal-authenticate-android-devices-fail)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
