# 如何将通知详细信息发送到Microsoft支持

## 概要

本文提供有关如何将通知详细信息发送到Microsoft支持的指导。

## 如何查看门户通知的详细信息

可以通过遵循以下步骤来查看任何门户通知的详细信息：

1. 选择**Azure 门户右上角的“通知**”图标（钟声）。
2. 选择处于“错误**”状态的任何通知（旁边带有红色（！）图标的通知**。

   注意

   不能单击状态为“成功”或“正在进行中”的通知。
3. 使用“通知详细信息”下的信息了解有关问题的详细信息。

如果仍需要帮助，还可以与支持工程师或产品组共享此信息以获取有关问题的帮助。

## 如何通过向支持工程师发送通知详细信息来获取帮助

1. **获取屏幕截图**或选择“**复制错误”图标**，在“复制错误**”文本框右侧**找到，以复制所有通知详细信息，以便与支持或产品组工程师共享。

如果需要帮助，请务必与支持工程师共享 **下面** 列出的所有详细信息，以便他们可以快速提供帮助。

## 介绍通知详细信息

有关通知的更多详细信息，请参阅以下说明。

### 基本通知项

- **标题** – 通知的描述性标题
  - 示例 – **应用程序代理设置**
- **说明** – 操作结果所发生情况的说明
  - 示例 – **输入的内部 URL 已被其他应用程序使用**
- **通知 ID** – 通知的唯一 ID
  - 示例 - **clientNotification-2adbfc06-2073-4678-a69f-7eb78d96b068**
- **客户端请求 ID** – 浏览器发出的特定请求 ID
  - 示例 – **302fd775-3329-4670-a9f3-bea37004f0bc**
- **时间戳 UTC** – 发生通知的时间戳（UTC）
  - 示例 – **2017-03-23T19:50:43.7583681Z**
- **内部事务 ID** – 可用于查找系统中的错误的内部 ID
  - 示例 – **71a2f329-ca29-402f-aa72-bc00a7aca603**
- **UPN** – 执行操作的用户
  - 示例 – **tperkins@f128.info**
- **租户 ID** – 执行操作的用户是其成员的租户的唯一 ID
  - 示例 – **aaaabbbb-0000-cccc-1111-dddd222eeee**
- **用户对象 ID** – 执行操作的用户的唯一 ID
  - 示例 – **cccccccc-2222-3333-4444-dddddddddddd**

### 详细通知项

- **显示名称** – **（可以为空）** 错误更详细的显示名称
  - 示例 – **应用程序代理设置**
- **状态** – 通知的特定状态
  - 示例 – **失败**
- **对象 ID** – **（可以为空）** 执行操作的对象 ID
  - 示例 – **8e08161d-f2fd-40ad-a34a-a9632d6bb599**
- **详细信息** – 操作结果所发生情况的详细说明
  - 示例 - **内部 URL `https://bing.com/` 无效，因为它已在使用中**
- **复制错误** – 选择**复制错误**文本框右侧**的复制图标**以复制所有通知详细信息，以便与支持或产品组工程师共享
  - 示例 `{"errorCode":"InternalUrl\_Duplicate","localizedErrorDetails":{"errorDetail":"Internal url 'https://google.com/' is invalid since it is already in use"},"operationResults":\[{"objectId":null,"displayName":null,"status":0,"details":"Internal url 'https://bing.com/' is invalid since it is already in use"}\],"timeStampUtc":"2017-03-23T19:50:26.465743Z","clientRequestId":"aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb","internalTransactionId":"bbbbbbbb-1111-2222-3333-cccccccccccc","upn":"tperkins@f128.info","tenantId":"aaaabbbb-0000-cccc-1111-dddd2222eeee","userObjectId":"cccccccc-2222-3333-4444-dddddddddddd"}`

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/send-notification-details)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
