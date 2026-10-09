# 将 Android 应用发布到 Google Play 应用商店后，身份验证失败

## 概要

本文提供了在用户安装发布到 Google Play Store 的 Android 应用后登录期间发生的身份验证失败的解决方案。

## 症状

请考虑以下情况：

- 已使用 Microsoft 身份验证库（MSAL）在 Android 应用中成功实现Microsoft Entra 身份验证。
- 应用已生成并执行并已通过所有 QA 测试。
- 将应用发布到 Google Play 商店。

在这种情况下，在用户安装应用后，登录到应用时身份验证不起作用。

如果向用户公开身份验证错误消息，或者允许他们向团队发送错误消息，可能会遇到如下文本的错误消息：

> 配置文件中的重定向 URI 与使用包名称和签名哈希生成的 URI 不匹配。 请在Azure 门户中验证配置文件中的 URI 和应用注册。

此问题的另一种可能方案是：

在开发和 QA 测试期间，将应用设置为使用支持的中转站来处理身份验证和单一登录（SSO）。 但是，通过 Google Play 部署应用并安装后，该应用不再使用中转站进行身份验证。

## 原因

在设备上生成用于安装的 Android 应用程序时，它将生成为 APK 压缩包，然后由证书签名。 此证书签名可确保生成应用程序的人员是拥有私钥的签名密钥的人员。 这可以防止黑客对应用程序进行有害修改，因为他们无法使用原始私钥对版本进行签名。

以前，Android 开发人员拥有和维护其私钥。 目前，Google Play Services 为 Android 开发人员生成和维护私钥，确保 Google 的安全存储。 开发人员仍保留上传密钥，以便 Google Play Services 可以验证上传的应用捆绑包的真实性，但在用户在其设备上安装应用时，由 Google 拥有的签名证书执行实际签名。

MSAL for Android Native 和 Microsoft 支持部门ed Authentication Brokers 使用已安装应用程序的公共签名哈希在身份验证期间与 Android作系统交互时标识它。

通过 Google Play 安装的应用程序的公共签名哈希不同于发布到 Google Play 之前安装的签名哈希。 因此，MSAL 将使用不正确的签名哈希进行配置。

## 解决方案

若要解决此问题，请执行以下作：

- [使用 MSAL 包检查器工具或 Google Play Console](#get-a-new-signature-hash-with-the-msal-package-inspector-tool-or-from-the-google-play-console) 获取新的签名哈希。
- [使用新签名哈希](#add-a-new-redirect-uri-to-the-app-registration-in-the-azure-portal-with-the-new-signature-hash)将新的重定向 URI 添加到Azure 门户中的应用注册。
- [更新应用程序代码中的 MSAL 配置，以使用新的重定向 URI 和签名哈希](#update-the-msal-configuration-within-the-application-code-to-use-the-new-redirect-uri-and-signature-hash)。

### 使用 MSAL 包检查器工具或 Google Play Console 获取新的签名哈希

可以使用 MSAL 包检查器工具或 Google Play Console 获取新的签名哈希。

若要安装和使用 MSAL 包检查器，请参阅 [MSAL Android 本机指南](package-inspector-msal-android-native)的包检查器。

若要从 Google Play Console 获取签名哈希，请执行以下步骤：

1. 转到 Google Play Console 并使用 Google Developer 帐户登录。
2. 进入 Google Play Console 后，选择受影响的应用。
3. 在左侧导航的“ **发布** ”类别下，展开 **“设置**”，然后选择“ **应用完整性**”。
4. **选择“应用签名**”选项卡。你将在三种不同的变体中看到应用签名密钥的指纹。
5. **复制 SHA-1 证书指纹**并将其粘贴到步骤 6 中的 PowerShell 脚本中作为变量的值`$Thumbprint`。
6. 运行以下脚本以获取 MSAL 所需的 base64 编码指纹：

   ```
   $Thumbprint = "paste your fingerprint here"
   $Thumbprint = $Thumbprint.Replace(":", "")

   $Bytes = [byte[]]::new($Thumbprint.Length / 2)

   For($i=0; $i -lt $Thumbprint.Length; $i+=2){
       $Bytes[$i/2] = [convert]::ToByte($Thumbprint.Substring($i, 2), 16)
   }

   $hashedString =[Convert]::ToBase64String($Bytes)

   Write-Host $hashedString
   ```

[![显示如何从 Google Play Console 获取签名哈希的屏幕截图。](media/android-app-authentication-fails-after-published-to-google-play-store/google-play-console-app-signing.png)](media/android-app-authentication-fails-after-published-to-google-play-store/google-play-console-app-signing.png#lightbox)

### 使用新签名哈希将新的重定向 URI 添加到Azure 门户中的应用注册

备注

建议添加新的重定向 URI，而不是修改现有的重定向 URI。 应用注册可以包含许多重定向 URI。 此外，修改现有的重定向 URI 可能会导致应用的开发版本出现问题。 这可能会导致故障排除、开发更新等过程中出现问题。

1. 登录到Azure 门户并导航到**应用注册**页。
2. 选择 Android 应用的应用注册。
3. 在“管理”下，选择“身份验证”。
4. 在“平台配置”下，选择“添加平台” 。
5. 在“配置平台**”下**，选择“**Android**”。

   ![显示如何配置 Android 平台的屏幕截图。](media/android-app-authentication-fails-after-published-to-google-play-store/app-reg-platform-config.png)
6. 输入 Android 应用的包名称。 此外，生成并输入签名哈希。

   ![显示如何配置 Android 应用的屏幕截图。](media/android-app-authentication-fails-after-published-to-google-play-store/app-registrations-configure-android-app.png)

   备注

   只要签名哈希不同，即可在多个 Android 重定向 URI 中使用同一个包名称。
7. 选择“配置”以完成平台配置。

### 更新应用程序代码中的 MSAL 配置以使用新的重定向 URI 和签名哈希

更新应用程序代码中的 MSAL 配置文件和 Android 清单文件。

- MSAL 配置文件：

  仅更改重定向 URI。 直接从Azure 门户复制并粘贴它。 在Azure 门户中，重定向 URI 的签名哈希部分经过 HTTP 编码。 它应保持 HTTP 编码。

  ```
  {
      "client_id": "<Client ID>",
      "authorization_user_agent": "DEFAULT",
      "redirect_uri": "<Redirect URI>"
      "broker_redirect_uri_registered": true,
      "authorities": [
          {
              "types": "AAD",
              "audience": {
                  "type": "AzureADMyOrg",
                  "tenant_id": "<Tenant ID>"
              }
          }
      ],
      "logging":{
          "log_level": "VERBOSE",
          "logcat_enabled": true
      }
  }
  ```
- Android 清单文件：

  仅更改 `android:path` 活动中的 `com.microsoft.identity.client.BrowserTabActivity` 属性。 将签名哈希粘贴为此属性的值。

  ```
  <activity
      android:name="com.microsoft.identity.client.BrowserTabActivity">
      <intent-filter>
          <action android:name="android.intent.action.VIEW" />
          <category android:name="android.intent.category.DEFAULT" />
          <category android:name="android.intent.category.BROWSABLE" />
          <data
              android:schema="msauth"
              android:host="com.example.azureauthsso1"
              android:path="android_path" />
      </intent-filter>
  </activity>
  ```

  备注

  - 请确保在签名哈希前面包含正斜杠。
  - 与重定向 URI 不同，此处的签名哈希不是 HTTP 编码的。

**第三方信息免责声明**

本文中提到的第三方产品由 Microsoft 以外的其他公司提供。 Microsoft 不对这些产品的性能或可靠性提供任何明示或暗示性担保。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/android-app-authentication-fails-after-published-to-google-play-store)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
