# 权限执行、SLA 算法与外部适配器契约

| 项目 | 约束 |
|---|---|
| 规范编号 | AX |
| 权限基线 | PRD 5、`SM-ROLE-001`；角色值引用 `DM-002` |
| SLA 基线 | PRD 11、`SM-TICKET-003`、`RD-004` |
| 外部故障 | `RD-003`、`RD-006`、`RD-007` |

## AX-001 授权判定

所有读取和写入都执行统一服务端判定器，输入为 principal、role、resourceType、resourceId、currentState、assignmentRelation 和 action。请求体中的 user ID、工程师 ID 或 owner scope 只能是筛选条件，不能作为授权事实。

顺序：认证有效 → 账号启用 → 角色有效 → 对象存在且可见 → 当前责任/历史关系 → 状态动作守卫 → 敏感动作二次确认 → 审计。失败返回 PRD 错误码，不向无权主体泄露对象存在性。

| 角色/关系 | 允许范围 | 明确禁止 |
|---|---|---|
| `EMPLOYEE` | 本人咨询/工单、聊天、补充、验收、撤销、规则允许恢复 | 他人对象、优先级、撤回原文 |
| 当前 `ENGINEER` | 当前负责对象处理、消息、等待、解决方案、申请转派 | 转派后私密聊天、管理员干预 |
| 历史工程师 | 历史处理字段和流转只读 | 普通聊天正文、附件、继续流转 |
| `PLATFORM_ADMIN` | 全量业务字段、异常队列、转派、优先级、异常关闭和规则恢复 | 绕过状态矩阵、物理删除 |
| `KNOWLEDGE_ADMIN` | 脱敏案例、知识审核/版本/搜索、AI评测配置 | 原始私密数据、作者自审 |

撤回原文、异常关闭、优先级修改、重新打开、角色授予/回收必须提供一次性二次确认凭证并审计，凭证不落库。

## AX-002 SLA 算法

服务日历由平台维护时区、工作日、工作时段、节假日和午休规则。默认值引用 PRD 11.1；重叠/逆序配置拒绝发布并返回 `SLA_CONFIG_INVALID`。

1. 用服务日历时区切分时间，非工作段不计入。
2. 合并重叠暂停区间，仅 `PENDING_SUPPLEMENT/PENDING_EXTERNAL` 可暂停。
3. 从创建/分配时间累计有效工作秒，得到 elapsedWorkSeconds 和截止时间。
4. 在 MySQL 事务内更新 SLA 投影；调度器只处理到期投影，不改变状态合法性。
5. 优先级变化建立新目标和版本，保留已消耗秒数和违约历史。

响应 SLA 在有效分配时启动，工程师首次有效动作达成；直接提单和咨询目标引用 PRD 11.2。完成 SLA 从正式建单起算，解决方案进入待验收时停止；验收等待不消耗，驳回后继续累计。具体目标值不重复定义。

调度器使用 MySQL 租约/版本条件；提醒失败进入通知补偿，不改变 SLA 结果。

## AX-003 外部适配器接口

适配器统一返回 `SUCCESS | RETRYABLE_FAILURE | PERMANENT_FAILURE | UNAVAILABLE`。SSO、CMDB、对象存储授权、恶意扫描和 RAG 是隔离的同步链路；HR、邮件和索引刷新由 Outbox 异步调用。外部调用不得持有 MySQL 主事务连接。

| 适配器 | 最小能力 | 成功写入 | 失败行为 |
|---|---|---|---|
| SSO | 校验会话/令牌、取得主体 | 认证上下文 | 未认证拒绝 |
| HR/组织 | 增量/全量同步 | 身份/组织投影、同步审计 | 保留最近快照，重试告警 |
| CMDB | 资产编号校验 | 资产结果或待核对标记 | 超时不阻塞提单 |
| 对象存储 | 预签名上传、短期下载 | 对象键和扫描状态 | 未扫描不得下载 |
| 恶意文件扫描 | MIME/哈希/病毒扫描 | AttachmentScanStatus | 超时按失败，允许重传 |
| 邮件 | 模板化高优先级通知 | 通知投影 | 站内继续，失败入补偿/DLQ |
| RAG/模型 | 检索已发布版本、受约束生成 | AI interaction 元数据 | 结构化拒答/不可用，不阻塞转人工 |

模型 provider 接入、baseUrl/Secret 安全、OpenAI-compatible chat/embeddings/SSE/health、索引 worker、ProviderResult 和 adapter 的统一结果由 `MR-001` 至 `MR-015` 定义；本规范只定义外部适配器的权限、超时边界和同步/异步分类。

每个适配器必须有超时、断路器、并发上限、脱敏日志和测试桩；默认超时、重试沿用 RD-003。供应商、认证协议、连接池和断路器容量是需父代理/用户定夺的部署参数。

## AX-004 契约测试

每个适配器覆盖成功、超时、连接拒绝、格式错误、鉴权失败、重复请求、断路器打开和恢复；主链路验证外部失败不阻塞 AC-29。HR 验证禁用账号及时生效且失败不覆盖快照；CMDB 验证待核对；对象存储验证未扫描不可下载；RAG 验证只返回已发布版本；模型 provider 的协议和安全测试引用 MR-009。

## AX-005 未决决策

- 旧角色/状态未知值处理（与 SQL-003 联动）。
- 旧企微/短信到一期 IN_APP/EMAIL 的映射。
- 服务日历时区、午休默认和节假日数据源。
- 外部供应商、认证协议、断路器容量和 Redis 运维参数。
- SLA 到期调度频率、事件保留期和归档分区策略。


## AX-006 可编码授权矩阵

动作代码全集：READ_BASIC、READ_CHAT、READ_ATTACHMENT、READ_HISTORY、SEND_MESSAGE、WITHDRAW_MESSAGE、CREATE_TICKET、RESOLVE、ACCEPT_TICKET、REQUEST_SUPPLEMENT、SUBMIT_SUPPLEMENT、START_EXTERNAL_WAIT、RESUME_TICKET、SUBMIT_RESOLUTION、ACCEPTANCE、CANCEL、REOPEN、REQUEST_TRANSFER、ADMIN_TRANSFER、ADMIN_PRIORITY、ADMIN_CLOSE、KNOWLEDGE_EDIT、KNOWLEDGE_REVIEW、KNOWLEDGE_PUBLISH、KNOWLEDGE_HIGH_RISK_REVIEW、AUDIT_WITHDRAWN_READ、CONFIG_WRITE、PRESENCE_WRITE。

| 资源归属/状态 | EMPLOYEE | CURRENT_ENGINEER | HISTORY_ENGINEER | PLATFORM_ADMIN | KNOWLEDGE_ADMIN |
|---|---|---|---|---|---|
| own consultation, non-terminal | READ_BASIC,READ_CHAT,SEND_MESSAGE,CANCEL,CREATE_TICKET | - | - | READ_BASIC | - |
| own consultation, RESOLVED within window | READ_BASIC,REOPEN | - | - | READ_BASIC | - |
| assigned consultation, non-terminal | - | READ_BASIC,READ_CHAT,SEND_MESSAGE,REQUEST_TRANSFER,RESOLVE | - | READ_BASIC | - |
| own ticket, non-terminal | READ_BASIC,READ_CHAT,SEND_MESSAGE,WITHDRAW_MESSAGE,SUBMIT_SUPPLEMENT,ACCEPTANCE,CANCEL | - | - | READ_BASIC | - |
| own ticket, COMPLETED/specific CLOSED in window | READ_BASIC,REOPEN | - | - | READ_BASIC | - |
| assigned ticket, mutable state | - | READ_BASIC,READ_CHAT,READ_ATTACHMENT,SEND_MESSAGE,ACCEPT_TICKET,REQUEST_SUPPLEMENT,START_EXTERNAL_WAIT,RESUME_TICKET,SUBMIT_RESOLUTION,REQUEST_TRANSFER | - | READ_BASIC | - |
| formerly assigned ticket | - | - | READ_HISTORY | READ_BASIC | - |
| completed/closed ticket | READ_BASIC | READ_HISTORY if formerly assigned | READ_HISTORY | READ_BASIC,REOPEN only where SM permits | - |
| withdrawn message original | - | - | - | AUDIT_WITHDRAWN_READ (dedicated view + audit) | - |
| masked case candidate | - | - | - | - | READ_BASIC,KNOWLEDGE_EDIT,KNOWLEDGE_REVIEW |
| PUBLISHED knowledge | READ_BASIC | READ_BASIC | READ_BASIC | READ_BASIC | READ_BASIC,KNOWLEDGE_EDIT,KNOWLEDGE_REVIEW,KNOWLEDGE_PUBLISH |
| engineer presence resource | - | PRESENCE_WRITE | - | READ_BASIC | - |
| config/roles/teams/SLA | - | - | - | CONFIG_WRITE | - |

Any combination not in this table is denied. Current assignment and state are evaluated from MySQL within the same transaction as writes. Platform administrators do not receive ordinary chat or attachment content; only the dedicated audit view can read withdrawn originals.

## AX-007 同步与异步适配器签名

同步适配器在请求链路执行，必须短超时且不可持有业务事务连接；异步适配器只由 Outbox 消费者调用。

~~~java
interface SsoAdapter {
  AuthContext authenticate(String bearer, String requestId);
}
interface CmdbAdapter {
  AssetCheckResult check(String assetId, String requestId);
}
interface ObjectStoreAdapter {
  UploadGrant createUploadGrant(String sha256, long sizeBytes, String contentType, String requestId);
  DownloadGrant createDownloadGrant(String objectKey, Duration ttl, String requestId);
}
interface MalwareScanAdapter {
  ScanResult scan(String objectKey, String sha256, String requestId);
}
interface HrAdapter {
  SyncPage pull(String cursor, int limit, String requestId); // async
}
interface MailAdapter {
  DeliveryResult send(MailRequest request, String dedupKey, String requestId); // async
}
interface RagAdapter {
  RagResult answer(PublishedKnowledgeQuery query, String requestId); // synchronous and isolated
}
~~~

DTO 只包含业务所需最小字段：适配器响应必须带 providerRequestId、status、errorClass、retryable 和 occurredAt；错误分类为 TIMEOUT、UNAVAILABLE、AUTH_FAILED、INVALID_RESPONSE、RATE_LIMITED、SECURITY_REJECTED、NOT_FOUND、PERMANENT. 认证使用企业 SSO 约定；供应商 URL/凭据从加密配置读取。同步调用失败按 RD-003 快速返回降级，异步失败进入 EV-004 DLQ。幂等键分别为 requestId（读）、sha256+bizId（上传/扫描）、eventId+receiverId+channel（邮件/通知）。

## AX-008 SLA 计算伪代码与测试向量

~~~text
effectiveSeconds(start,end,calendar):
  cursor = start in calendar.timezone
  total = 0
  while cursor < end:
    day = localDate(cursor)
    for interval in calendar.intervals(day):
      segment = intersection([cursor,end], interval)
      total += seconds(segment) minus mergedPauseOverlap(segment)
    cursor = nextLocalDay(day, calendar.timezone)
  return max(total,0)

deadline(start,target,calendar,pauses):
  cursor = start
  remaining = target
  while remaining > 0:
    segment = nextWorkingSegment(cursor, calendar) // handles midnight/DST
    usable = segment.seconds minus pauseOverlap(segment, pauses)
    if usable >= remaining: return advanceWithinSegment(segment.start, remaining, mergedPauses) in Instant
    remaining -= usable; cursor = segment.end
~~~

暂停区间先按 Instant 排序合并；跨午休、周末、节假日和 DST 时按服务时区切片后再换算 Instant。测试向量至少包括：周五 17:30 + 2 工作小时→下周一 10:30；午休重叠暂停；春节整日；DST 前后各一天；暂停覆盖非工作时段；优先级变更保留已消耗秒数。所有向量保存 calendar 版本和预期 Instant。
