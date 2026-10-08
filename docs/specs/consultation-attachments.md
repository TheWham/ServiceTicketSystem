# 人工咨询附件

员工与当前工程师可将图片或文件拖入聊天输入区，或点击回形针选择文件。选择后立即上传为个人草稿；发送时与文字一起绑定到消息，也可只发送附件。上传中和失败未处理的草稿不允许发送。每条消息最多10个文件、每文件20MB。

图片使用受权 Blob 展示缩略图、点击预览；普通文件显示名称、大小和下载按钮。历史消息保留附件，刷新后可继续查看。AI 阶段不接受附件解析，此能力用于人工咨询。

## HTTP 接口

路径前缀 `/api/v1/consultations/{sessionId}/attachments`，沿用 JWT 网关认证及 `X-Request-Id`。

| 方法 | 路径 | 行为 |
|---|---|---|
| POST | 前缀本身 | multipart 字段 `file`，上传会话内个人草稿 |
| DELETE | `/{attachmentId}` | 移除本人尚未发送的草稿 |
| GET | `/{attachmentId}/content` | 受会话权限约束的二进制读取 |

上传返回咨询服务包络，data 字段：

```json
{"attachment_id":"ATT...","file_name":"报错截图.png","content_type":"image/png","size":1234,"is_image":true}
```

原消息接口 `POST /api/v1/consultations/{sessionId}/messages` 支持：

```json
{"client_message_id":"client-generated-id","content":"请看附件","attachment_ids":["ATT..."]}
```

`content` 与 `attachment_ids` 至少提供一个；仅附件消息应省略空 `content`。响应及历史消息增加 `attachments` 元数据数组。重试沿用同一个 `client_message_id`，更换正文或附件后生成新 ID。

## 存储与访问

- 复用 `attachment` 表；草稿命名空间隔离会话与上传人，发送事务绑定到 `MESSAGE`。
- 消息 `citation_json` 以 schemaVersion=1 保存附件元数据，兼容原有 AI 引用与反馈元数据，不新增数据库字段。
- 附件仅对当前有权参与该会话的用户可读，未发送草稿仅上传者可读；其他会话不能引用这些 ID。
- 本地文件在 consultation-service 工作目录的 `data/attachments/consultation` 下，已被 Git 忽略。可用 `itticket.attachment.storage-dir` 指定持久化目录。
- 本地部署沿用现有附件的类型/大小校验模式，未增加病毒扫描引擎。普通文件强制下载，图片预览仅允许识别的位图类型，不内联 HTML/SVG。

## 验证

前端：`node --test tests/chat-attachments.test.mjs tests/consultation-attachment-api.test.mjs tests/consultation-lifecycle.test.mjs tests/engineerViews.test.mjs`。

后端：在 `it-ticket-cloud` 执行 `mvn -pl consultation-service -am test`。

验收场景：工程师附件首条回复完成接入；员工拖入截图并发送；双方预览/下载；刷新后附件历史可恢复；非参与者下载被拒绝。
