# MSAL Android Native 的包检查器

## 概要

适用于 Android Native 的Microsoft身份验证库（MSAL）包含一个名为“包检查器”的工具。 此工具列出了在 Android 设备上安装的包，允许用户查看、复制和粘贴用于对应用程序包进行签名的签名哈希。 包检查器对于排查和验证 Android 设备上安装的应用程序的签名哈希非常有用。 本文介绍包检查器的安装、使用情况和常见问题。

## 使用包检查器的方案

- 已成功开发应用程序以使用 MSAL，但在将应用部署到 Google Play Store 后，应用无法执行身份验证。

  在此方案中，包检查器可用于发现 Google 用于对应用包进行签名的新签名哈希。
- 你在 Android 应用程序中实现 MSAL，但遇到以下错误：

  > 配置文件中的重定向 URI 与使用包名称和签名哈希生成的 URI 不匹配。 请在Azure 门户中验证配置文件中的 URI 和应用注册。

  在此方案中，可以使用包检查器来验证包签名哈希是什么，并将 Azure 门户和应用程序配置为使用正确的签名哈希。
- 你在 Android 应用程序中实现 MSAL，但遇到以下错误：

  > 意向筛选器：缺少 BrowserTabActivity

  发生此错误的原因是 *AndroidManifest.xml* 文件中指定的签名哈希与用于对 APK 文件进行签名的签名哈希不匹配。 在此方案中，包检查器可用于验证签名哈希是什么。

注释

有关适用于 Android 本机的 MSAL 的详细信息，请参阅适用于 Android [的](https://github.com/AzureAD/microsoft-authentication-library-for-android)Microsoft身份验证库（MSAL）。

## 先决条件

在开始之前，请确保具有以下各项：

- 已安装最新版本的 Android Studio。

  Android Studio 附带 AVD 管理器。 有关详细信息，请参阅 [创建和管理虚拟设备](https://developer.android.com/studio/run/managing-avds)。
- 安装了应用程序的虚拟 Android 设备。
- 启用了开发人员选项、启用 USB 调试和 USB 电缆的物理设备。 有关详细信息，请参阅 配置设备上的开发人员选项。
- 安装用于检查的应用程序。

## 安装包检查器

安装包检查器的方法有两种：

### 选项 1：将 Android MSAL 存储库直接克隆到 Android Studio 中

1. 打开 Android Studio 并关闭任何打开的项目。
2. 选择 **从版本控制**获取。

   ![屏幕截图，显示 Android Studio](media/package-inspector-msal-android-native/get-from-version-control.png)
    中的“从版本控制”选项
3. 确保在窗口顶部选择 **Git**，粘贴 Android MSAL 存储库 URL `https://github.com/AzureAD/microsoft-authentication-library-for-android.git`，然后选择 **克隆**。

   ![显示如何在 Android Studio](media/package-inspector-msal-android-native/clone-msal-repository.png)
    中克隆 Git 存储库的屏幕截图

### 选项 2：下载 Android MSAL 存储库并在 Android Studio 中打开它

1. [下载 Android MSAL 存储库](https://github.com/AzureAD/microsoft-authentication-library-for-android/archive/refs/heads/dev.zip)。
2. 将 zip 文件解压缩到所选目录。
3. 打开 Android Studio 并关闭任何打开的项目。
4. 选择 **打开现有项目**。

   ![显示 Android Studio](media/package-inspector-msal-android-native/open-existing-project-android-studio.png)
    中的“打开现有项目”选项的屏幕截图
5. 为 Android MSAL 存储库选择 **msal-android** 的根包。 然后，选择“确定”。

   ![显示在 Android Studio](media/package-inspector-msal-android-native/select-root-package.png)
    中选择根包的屏幕截图

   注释

   - 根包的默认名称为 `microsoft-authentication-library-for-android-dev`。 在此示例中，它重命名为 `msal-android`。
   - 不要选择 **包检查器** 目录。

## 使用包检查器

1. 在 Android Studio 中打开 Android MSAL 项目后，连接所需的 Android 设备。 它可以是连接到计算机的 USB 端口的物理设备，也可以是从 Android Studio 的 AVD 管理器启动的仿真器。 确保设备显示在 Android Studio 顶部的下拉列表中，然后选择它。
2. 在设备下拉列表的左侧，还有另一个下拉列表。 从中选择 **包检查器**。

   [![显示 Android Studio](media/package-inspector-msal-android-native/select-package-inspector.png)](media/package-inspector-msal-android-native/select-package-inspector.png#lightbox)
    中包检查器的选择的屏幕截图
3. 选择 **播放** 按钮（右侧带有绿色圆圈）以在所选设备上生成、安装和运行包检查器。

   显示 Android StudioScreenshot that shows the selection of the play button in Android Studio[![Screenshot that shows the selection of the play button in Android Studio](media/package-inspector-msal-android-native/select-play-button.png)Screenshot that shows the selection of the play button in Android Studio中播放按钮选择的屏幕截图](media/package-inspector-msal-android-native/select-play-button.png#lightbox)屏幕截图
4. 浏览包检查器应用中的包列表，并选择一个包以查看其签名哈希。 所有可访问的包都显示在此列表中。

   ![显示包检查器应用中的包选择的屏幕截图](media/package-inspector-msal-android-native/select-package-to-check-signature-hash.png)

## 常见问题

### 将包检查器加载到 Android Studio 时出现的问题

若要解决这些问题，请确保从 MSAL 存储库而不是包检查器加载根包。 确保加载到 Android Studio 中的 Android MSAL 项目命名为 `microsoft-authentication-library-for-android-dev` 或任何已重命名系统上的根目录，而不是 `package-inspector`。 有关详细信息，请参阅 [安装包检查器](#option-2-download-android-msal-repository-and-open-it-in-android-studio) 部分中 [选项 2](#install-package-inspector) 下的步骤 5。

### 并非所有包都显示在包检查器中

已安装并打开了包检查器，并且应用中显示的包列表。 但是，你看不到设备上已安装的任何应用的包。 此问题可能是由于 Android 11（API 30）中的更改导致的。 有关详细信息，请参阅 [包可见性](https://developer.android.com/training/package-visibility)。

若要解决此问题，请执行以下步骤：

1. 在 Android Studio 左侧的  目录中打开 `package-inspector` 文件。
2. 在 `<manifest></manifest>` 标记之间添加以下权限和查询：

   ```
   <manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.microsoft.inspector"></manifest>
   ...

   <permission android:name="android.permission.QUERY_ALL_PACKAGES" />

   <queries>
       <intent>
           <action android:name="android.intent.action.MAIN" />
       </intent>
   </queries>
   ```
3. 从 Android Studio 重新运行应用程序以应用更改。 然后，可以看到已安装的包。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/package-inspector-msal-android-native)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
