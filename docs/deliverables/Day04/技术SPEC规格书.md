# IT 服务工单系统 技术 SPEC 规格书

| 项目 | 内容 |
| --- | --- |
| 版本 | V1.1(P0 范围) |
| 日期 | 2026-09-21 |
| 范围 | **仅覆盖 P0:工单流转主链路**(提单 → 接单 → 处理/补充/转外部 → 验收 → 关闭)及其数据结构、超时与降级逻辑。企业微信/短信触达渠道、知识库 RAG 智能推荐等非 P0 能力**整体后置**,不在本规格书定义范围内 |
| 关联文档 | 《IT 服务工单系统 PRD-修订版》(P0 部分)、`docs/api.md`(接口契约)、`docs/schema.sql`(建表 DDL)、《案件状态转移表》(code_artifact.md,§3 表格模板) |
| 实现基线 | `backend/`(Spring Boot 3.3 + MyBatis-Plus + MySQL 8)、`frontend/`(Vue 3 + Element Plus) |

---

# 1. 核心实体数据结构

## 1.0 全局约定

| 约定项 | 规格 |
| --- | --- |
| 字符集 | 全库 utf8mb4 / utf8mb4_unicode_ci(SQL 导入必须 `--default-character-set=utf8mb4`) |
| 时间格式 | 接口出入参统一 `yyyy-MM-dd HH:mm:ss`(Jackson 全局配置),时区 GMT+8(Asia/Shanghai) |
| 主键策略 | 业务主键(ticket_id / user_id / asset_id)为 VARCHAR,由应用生成;日志类表用 BIGINT AUTO_INCREMENT;MyBatis-Plus 雪花 ID 仅用于无业务主键要求的记录表(`id-type: assign_id`) |
| 枚举存储 | 所有枚举在 DB 中存 `name()` 字符串(如 `ASSIGNED`),禁止 ordinal |
| 统一响应 | `{ code, msg, data }`,`code=0` 成功;业务失败走 §2.7 错误码表 |
| 命名 | DB 下划线、Java/TS 驼峰,MyBatis-Plus `map-underscore-to-camel-case` 自动映射 |

## 1.1 工单表 `ticket`(主实体)

| 字段 | 类型 | 可空/默认 | 约束(正则 / 值域) | 说明 |
| --- | --- | --- | --- | --- |
| ticket_id | VARCHAR(32) | PK | `^TK\d{8}\d{4}$` | 工单号:TK + yyyyMMdd + 当日 4 位序号(如 TK202609190001),由 `ticket_id_seq` 表原子自增发号,见 §1.6 |
| title | VARCHAR(50) | NOT NULL | 长度 1–50 | 工单标题,用于列表/详情/通知文案 |
| category | VARCHAR(20) | NOT NULL | 值域 `HARDWARE/SOFTWARE/NETWORK/ACCOUNT/OTHER` | 工单分类 |
| asset_id | VARCHAR(32) | NULL | `^IT-[A-Z]{2,4}-\d{8}$`,KEY idx_asset | 关联资产编号;提交时经 `/api/asset/{id}` 校验,查无 → 40401 |
| description | VARCHAR(500) | NOT NULL | 长度 10–500 | 问题描述 |
| attachment_urls | VARCHAR(1000) | NULL | JSON 数组串,元素 ≤3 个,元素形态 `/files/{32位hex}.{jpg\|jpeg\|png}` | 附件 URL 列表(先经 `/api/attachment/upload` 上传取得) |
| priority | VARCHAR(10) | NOT NULL,默认 `MEDIUM` | 值域 `HIGH/MEDIUM/LOW` | 优先级 |
| expected_finish_time | DATETIME | NULL | 必须 ≥ 当前时间(`@FutureOrPresent`) | 期望完成时间;超时工单视图判定字段 |
| ticket_status | VARCHAR(30) | NOT NULL,默认 `CREATED` | 值域见 §1.8,流转合法性由 `TicketStateMachine` 强制校验(§3) | 工单状态 |
| creator_id | VARCHAR(32) | NOT NULL | 关联 sys_user.user_id,KEY idx_creator | 提单人 |
| assignee_id | VARCHAR(32) | NULL | 关联 sys_user.user_id,KEY idx_assignee_status | 处理人;CREATED 阶段为 NULL(待接单公共池) |
| reject_count | INT | 默认 0 | ≥0 | 验收被驳回次数(ACCEPT_REJECT 时 +1) |
| version | INT | 默认 0 | 乐观锁 | `updateById` 受影响行数=0 → 40900「工单已被他人操作」 |
| create_time / update_time | DATETIME | NOT NULL | — | 创建/最近更新时间(超时扫描以 update_time 为准) |

## 1.2 工单流转日志表 `ticket_log`

| 字段 | 类型 | 可空/默认 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| id | BIGINT | PK,AUTO_INCREMENT | — | 主键 |
| ticket_id | VARCHAR(32) | NOT NULL | KEY idx_ticket(ticket_id, create_time) | 所属工单 |
| operator_id / operator_name | VARCHAR(32) | NOT NULL / 可空 | — | 操作人 ID 与冗余姓名 |
| action | VARCHAR(30) | NOT NULL | 值域 `TicketActionMeta` 枚举:SUBMIT/ACCEPT/REQUEST_SUPPLEMENT/SUPPLEMENT/TRANSFER_EXTERNAL/RESUME/RESOLVE/ACCEPT_APPROVE/ACCEPT_REJECT/REWORK/CLOSE | 操作类型 |
| from_status / to_status | VARCHAR(30) | 可空 | 值域同 ticket_status | 变更前后状态(SUBMIT 时 from 为 NULL) |
| remark | VARCHAR(500) | 可空 | — | 备注;REQUEST_SUPPLEMENT / TRANSFER_EXTERNAL / ACCEPT_REJECT 三动作**强制非空**,缺省回填动作默认文案 |
| attachment_urls | VARCHAR(1000) | 可空 | 同 §1.1 | 本次操作追加的附件 |
| create_time | DATETIME | NOT NULL | — | 操作时间,详情页时间线按此升序 |

## 1.3 用户表 `sys_user`

| 字段 | 类型 | 可空/默认 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| user_id | VARCHAR(32) | PK | 工号形态,如 `E1001` | 登录与业务关联主键 |
| username | VARCHAR(32) | NOT NULL | UNIQUE uk_username | 登录名(登录支持工号或登录名二选一) |
| password | VARCHAR(100) | NOT NULL | BCrypt 哈希 | 禁存明文 |
| real_name | VARCHAR(32) | 可空 | — | 真实姓名(token 不含,展示时按 user_id 回查) |
| role | VARCHAR(16) | NOT NULL | 值域 `EMPLOYEE/ENGINEER/SUPERVISOR` | 角色;流转动作权限校验依据(§3.2-4) |
| phone | VARCHAR(20) | 可空 | — | P0 仅存字段,不用于触达 |
| status | TINYINT | 默认 1 | 值域 `1启用 / 0禁用` | — |
| create_time / update_time | DATETIME | NOT NULL | — | — |

## 1.4 资产表 `asset`(Mock CMDB)

| 字段 | 类型 | 可空/默认 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| asset_id | VARCHAR(32) | PK | `^IT-[A-Z]{2,4}-\d{8}$`(如 IT-PC-20260901) | 资产编号 |
| asset_name | VARCHAR(100) | NOT NULL | — | 资产名称 |
| brand_model | VARCHAR(100) | 可空 | — | 品牌型号(提单页校验通过后回显) |
| owner_id | VARCHAR(32) | 可空 | 关联 sys_user.user_id | 使用人 |
| status | VARCHAR(16) | 默认 `IN_USE` | 值域 `IN_USE/IDLE/REPAIRING/SCRAPPED` | 资产状态 |
| create_time | DATETIME | NOT NULL | — | — |

## 1.5 流转事件记录表 `notify_record`(P0 仅落库)

| 字段 | 类型 | 可空/默认 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| id | BIGINT | PK,AUTO_INCREMENT | — | 主键 |
| ticket_id | VARCHAR(32) | NOT NULL | KEY idx_ticket | 关联工单 |
| event_type | VARCHAR(30) | NOT NULL | 值域见 §1.8 NotifyEventType(流转钩子事件) | 事件类型 |
| receiver_id | VARCHAR(32) | NOT NULL | KEY idx_receiver(receiver_id, create_time) | 接收人工号 |
| channel_used | VARCHAR(20) | NOT NULL | **P0 恒为 `LOG`**(落库 + 日志);`WECHAT/SMS` 值域保留、渠道后置 | 实际投递渠道 |
| is_fallback | TINYINT | 默认 0 | P0 恒为 0(渠道降级链后置) | 是否降级渠道 |
| delivery_status | VARCHAR(20) | NOT NULL | 值域 `SUCCESS/FAILED` | 投递状态 |
| title / content | VARCHAR(100) / VARCHAR(500) | 可空 | content 由事件模板渲染,占位符 `{ticketId}`、`{title}` | 通知标题/正文 |
| dedup_key | VARCHAR(64) | 可空 | 形态 `notify:{ticketId}:{eventType}:{receiverId}` | 去重键(60s 幂等,见 §2.4) |
| create_time | DATETIME | NOT NULL | — | 生成时间 |

> P0 定位:该表是**流转事件的落库凭证**(用于时间线旁证与验收断言),不承担对外触达;企业微信/短信投递与降级不在 P0 范围。

## 1.6 基础设施表(替代 Redis 的三件套)

**ticket_id_seq(发号表)**

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| seq_date | CHAR(8) PK | `yyyyMMdd` | 日期键 |
| seq | INT 默认 0 | — | 当日已发号数量;`INSERT ... ON DUPLICATE KEY UPDATE seq=seq+1` 原子自增后回读,JVM 内 `synchronized` 防串号 |

**dedup_lock(通用去重锁表)** — 键约定即值域约束:

| 键形态 | TTL | 用途 | 未抢到锁的行为 |
| --- | --- | --- | --- |
| `submit:{userId}:{title.hashCode}` | 3 秒 | 提单防重复提交 | 拒绝,返回 40900「请勿重复提交」 |
| `notify:{ticketId}:{eventType}:{receiverId}` | 60 秒 | 流转事件幂等落库 | 跳过该接收人本次记录 |

字段:lock_key VARCHAR(128) PK、expires_at DATETIME(KEY idx_expires)、create_time。获取语义:`INSERT IGNORE` 占位,已存在则仅允许「过期后抢占续期」;过期行由定时任务每小时清理(§2.5)。

**ticket_draft(草稿表)**:creator_id VARCHAR(32) PK(**一人一份**,提单成功后自动删除)、draft_content TEXT(表单 JSON 快照,允许残缺字段不做校验)、update_time DATETIME。

## 1.7 提单接口 DTO 校验矩阵(`POST /api/ticket`,TicketCreateDTO)

与 PRD「字段级校验与交互反馈表」一一对应,前后端同规则:

| 字段 | 必填 | 长度/范围 | 正则/值域 | 校验失败响应 |
| --- | --- | --- | --- | --- |
| title | 是 | 1–50 字符 | — | 40000 +「工单标题不能为空/长度需在 1~50 之间」 |
| category | 是 | — | `HARDWARE/SOFTWARE/NETWORK/ACCOUNT/OTHER` | 40000 |
| assetId | 否 | — | `^IT-[A-Z]{2,4}-\d{8}$` | 40000;另经 CMDB 查无 → 40401 |
| description | 是 | 10–500 字符 | — | 40000 |
| attachmentUrls | 否 | ≤3 个元素 | 元素须为先前上传返回的 `/files/**` URL | 40000「附件最多上传 3 个」 |
| priority | 是 | — | `HIGH/MEDIUM/LOW`,默认 MEDIUM | 40000 |
| expectedFinishTime | 否 | ≥ 当前时间 | `@FutureOrPresent` | 40000「期望完成时间不能早于当前时间」 |

附件上传本身(`POST /api/attachment/upload`,multipart 字段名 `file`):扩展名白名单 `.jpg/.jpeg/.png`,单张 ≤5MB,单次请求 ≤15MB(Spring multipart 上限);落盘为 `UUID32 + 原扩展名`,访问 URL `/files/{filename}`(免登录静态映射)。

## 1.8 枚举值域汇总

| 枚举 | 值域 | 备注 |
| --- | --- | --- |
| TicketStatus(8 态) | CREATED 待接单 / ASSIGNED 处理中 / PENDING_SUPPLEMENT 待补充 / PENDING_EXTERNAL 待外部 / PENDING_ACCEPTANCE 待验收 / ACCEPTED 已完成 / REJECTED 已驳回 / CLOSED 已关闭 | 终态:ACCEPTED(仅可 CLOSED)、CLOSED |
| TicketCategory | HARDWARE 硬件 / SOFTWARE 软件 / NETWORK 网络 / ACCOUNT 账号 / OTHER 其他 | — |
| Priority | HIGH 高 / MEDIUM 中(默认)/ LOW 低 | — |
| NotifyEventType(8 事件) | SUBMIT_SUCCESS / DISPATCH / PENDING_SUPPLEMENT / PENDING_EXTERNAL / PENDING_ACCEPTANCE / ACCEPT_APPROVED / ACCEPT_REJECTED / TIMEOUT_ALERT | 每事件携带文案模板(占位符 `{ticketId}`/`{title}`);P0 仅落库 |
| SysRole | EMPLOYEE / ENGINEER / SUPERVISOR | SUPERVISOR 对全部流转动作放行 |
| AssetStatus | IN_USE / IDLE / REPAIRING / SCRAPPED | — |
| DeliveryStatus | SUCCESS / FAILED | 落库状态 |

# 2. 超时与降级(Fallback)响应逻辑

> 本节仅覆盖 P0 工单流转链路上的超时与降级;渠道类降级(企业微信/短信)不在本版本范围。

## 2.1 超时阈值矩阵

| # | 场景 | 阈值 | 检测方 | 超时/失败后的响应逻辑 | 降级(Fallback) | 配置项 |
| --- | --- | --- | --- | --- | --- | --- |
| T1 | 提单重复提交 | **3s** 窗口(同用户 + 同标题) | 后端 dedup_lock | 拒绝,40900「请勿重复提交」 | 无(直接拒绝,保护幂等) | 锁 TTL 常量 3s |
| T2 | 工单处理中超时 | ASSIGNED 且 update_time 早于 **now-2h** | 定时任务,每分钟扫描 | 生成 TIMEOUT_ALERT 事件 → 主管(E9001)落库 | 扫描异常单次吞掉(§2.5);**不自动销毁工单** | `ticket.timeout.hours` |
| T3 | 待外部处理滞留 | PENDING_EXTERNAL 且 update_time 早于 **now-24h** | 定时任务,每 30 分钟扫描 | 重新生成 PENDING_EXTERNAL 事件(提单人+处理人) | 60s 幂等键防止重复记录轰炸;不自动流转 | `ticket.external.remind-hours` |
| T4 | 前端 HTTP 调用 | axios 全局 **15s** | 前端 request.ts | ElMessage 提示后端 msg 或「网络错误」,Promise reject 由页面兜底 | 401/40100 → 清 token+user,整页跳 `/login`(**防重入标记**,避免轮询接口造成跳转死循环) | — |
| T5 | 登录会话 | JWT 有效期 **12h**(HS256,claims 仅 userId/role/exp) | 后端拦截器 | 过期/签名非法 → HTTP 401 + `{code:40100}` | 前端按 T4 清会话重登录 | — |
| T6 | 附件上传 | 单张 ≤5MB / 单请求 ≤15MB | 后端 | 超限 → 40000「单张不超过 5MB」;格式非 jpg/jpeg/png → 40000「仅支持 jpg/png 格式」;IO 异常 → 40000「附件上传失败,请稍后重试」 | 前端 Toast 提示,表单与已传附件不丢 | `spring.servlet.multipart.*` |

## 2.2 提单链路降级

1. **校验失败不建单**:任意字段校验不过(DTO 校验 / CMDB 查无)直接返回 40000 / 40401,不产生工单与日志。
2. **防重优先**:同一用户 3s 内同标题(标题 hashCode 入键)重复提交一律 40900;宁可拒绝也不产生重复工单。
3. **草稿兜底**:表单内容可随时存草稿(`ticket_draft`,20 秒级自动保存 + 手动保存),提交失败不丢内容;提单成功后自动清除草稿。
4. **校验前置**:assetId 在失焦时即调 CMDB 校验,避免提交后才失败。

## 2.3 并发冲突降级

| 机制 | 键/字段 | 窗口 | 冲突响应 | 用户侧表现 |
| --- | --- | --- | --- | --- |
| 前端按钮防抖 | — | 3s | Loading「提交中…」期间禁点 | 防重复点击 |
| 后端防重锁 | `submit:{userId}:{title.hashCode}` | 3s | 40900「请勿重复提交」 | Toast 提示,表单内容不丢 |
| 乐观锁 | `ticket.version` | 全程 | update 影响行数=0 → 40900「工单已被他人操作,请刷新后重试」 | Toast 提示刷新 |
| 非法状态流转 | TicketStateMachine 状态边(§3) | 全程 | 40900「非法状态流转:X -> Y」 | Toast 提示,工单状态不变 |

## 2.4 流转事件落库降级(P0)

```
工单流转(transit 事务内)
   │  注册 afterCommit 回调(事务提交后才触发)
   ▼
事件生成 ──@Async("taskExecutor")──▶ 异步线程池 notify-(core 8 / max 16 / queue 200)
   │  全程 try-catch:任何异常仅记日志,绝不影响主事务与流转结果
   ▼
事件矩阵解析接收人(SUBMIT_SUCCESS→提单人;DISPATCH/PENDING_ACCEPTANCE/ACCEPT_REJECTED→处理人;
PENDING_SUPPLEMENT/ACCEPT_APPROVED→提单人;PENDING_EXTERNAL→提单人+处理人;TIMEOUT_ALERT→主管)
   │
   ▼  逐接收人:幂等抢锁 `notify:{ticketId}:{event}:{receiverId}`(TTL 60s)→ 抢不到则跳过 → 落 notify_record
```

**降级要点**:线程池满/异步异常/落库失败均只记日志,主链路(状态流转、ticket_log)不受影响;事件全丢也不阻塞工单闭环。接口层通过 `GET /api/notify/list` 只读展示,不参与流转判定。

## 2.5 定时任务兜底

1. **单次失败不影响调度**:T2/T3 扫描与 dedup_lock 清理(`cleanExpired`,cron `0 17 * * * ?`,每小时)均在方法内吞异常、记 error 日志。
2. **扫描只读不改状态**:超时任务仅生成事件记录,绝不隐式改变 ticket_status,避免绕过状态机。

## 2.6 数据容错解析

`ticket.attachment_urls` 读取时优先按 JSON 数组解析,失败自动降级为逗号分隔串解析;脏数据不导致详情页 500。未被识别的异常由 `GlobalExceptionHandler` 统一兜底返回 `code=500「系统繁忙,请稍后重试」`,不向前端泄露堆栈。

## 2.7 错误码与 HTTP 状态总表

| code | HTTP | 含义 | 典型触发 |
| --- | --- | --- | --- |
| 0 | 200 | 成功 | — |
| 40000 | 200 | 业务错误(通用) | DTO 校验失败、附件超限/格式错误、缺少必填 remark |
| 40100 | 200/401 | 未登录或登录已过期 | 密码错误;token 缺失/非法/过期(拦截器返回 HTTP 401 + 该码) |
| 40300 | 200 | 无权限访问 | 非本人工单查看/操作;角色不符(如员工执行接单) |
| 40400 | 200 | 资源不存在 | 工单号不存在 |
| 40401 | 200 | 资产不存在 | asset_id 未命中 CMDB |
| 40900 | 200 | 数据冲突 | 重复提交、非法状态流转、乐观锁冲突 |
| 500 | 200 | 系统繁忙 | 未捕获异常兜底 |

> 说明:业务错误统一以 HTTP 200 + 业务码返回(拦截器 401 除外),前端 `request.ts` 按 `code!==0` 统一 ElMessage 报错并 reject;`40100` 额外触发清会话跳登录。

## 2.8 验收入口

| 验收项 | 脚本 | 覆盖点 |
| --- | --- | --- |
| 端到端 17 步 | `python scripts/e2e_test.py` | 字段校验拦截(§1.7)、3s 防重(T1)、非法流转 40900、流转事件落库、工作台三分栏 |
| 修复回归 | `python scripts/verify_fixes.py` | 工作台口径、附件上传 |
| UI 冒烟 | `python scripts/ui_smoke_test.py` | 登录→提单→成功页→详情页 |
| 工作台 UI | `python scripts/verify_workbench_ui.py` | 工程师三分栏 |

---

# 3. 工单状态转换表(State Transition)

> 表格模板参照《案件状态转移表》(code_artifact.md);状态/动作取值与代码强一致:合法边定义于 `TicketStateMachine`,动作元数据(目标状态/角色/事件)定义于 `TicketActionMeta`,全部流转收口于 `TicketServiceImpl.transit()`。

## 3.1 状态转换主表

| 初始状态 | 触发动作 | 目标状态 | 异常 / 降级 / Log |
| :--- | :--- | :--- | :--- |
| 草稿 / 无(员工提单) | 提交成功 SUBMIT(仅 EMPLOYEE) | CREATED 待接单 | 字段校验失败不建单(40000);3s 内同标题重复提交 → 40900;落 `ticket_log(from=NULL)`;afterCommit 异步生成 SUBMIT_SUCCESS 事件 → 提单人;提单成功自动清该用户草稿 |
| CREATED 待接单 | 接单 ACCEPT(仅 ENGINEER) | ASSIGNED 处理中 | 角色不符 → 40300;并发抢单由乐观锁裁决,败者 40900「工单已被他人操作」;assignee_id 落当前工程师;生成 DISPATCH 事件 → 工程师 |
| ASSIGNED 处理中 | 请求补充 REQUEST_SUPPLEMENT | PENDING_SUPPLEMENT 待补充 | remark 必填,缺 → 40000「请填写说明」;生成 PENDING_SUPPLEMENT 事件 → 提单人 |
| PENDING_SUPPLEMENT 待补充 | 员工补充 SUPPLEMENT(提单本人) | ASSIGNED 处理中 | 非本人 → 40300;附件随 remark 写入流转日志;无事件 |
| ASSIGNED 处理中 | 转外部 TRANSFER_EXTERNAL | PENDING_EXTERNAL 待外部 | remark 必填;生成 PENDING_EXTERNAL 事件 → 提单人+处理人;超 24h 未更新由定时任务每 30 分钟重新生成(T3,60s 幂等) |
| PENDING_EXTERNAL 待外部 | 恢复处理 RESUME | ASSIGNED 处理中 | 无事件 |
| ASSIGNED 处理中 | 提交方案/验收 RESOLVE | PENDING_ACCEPTANCE 待验收 | 后置动作:afterCommit 异步生成 PENDING_ACCEPTANCE 事件 → 提单人(§3.2-3) |
| REJECTED 已驳回 | 返工 REWORK(工程师「重新处理」) | ASSIGNED 处理中 | 复用 DISPATCH 事件 → 工程师 |
| PENDING_ACCEPTANCE 待验收 | 验收通过 ACCEPT_APPROVE(提单本人) | ACCEPTED 已完成(**终态**,仅可关闭) | 非提单本人 → 40300;生成 ACCEPT_APPROVED 事件 → 工程师 |
| PENDING_ACCEPTANCE 待验收 | 验收驳回 ACCEPT_REJECT(提单本人) | REJECTED 已驳回 | remark 必填;reject_count +1;生成 ACCEPT_REJECTED 事件 → 工程师 |
| ACCEPTED 已完成 | 关闭 CLOSE(提单本人) | CLOSED 已关闭(**终态**) | 终态不可逆,无后续合法边 |
| REJECTED 已驳回 | 关闭 CLOSE(放弃验收) | CLOSED 已关闭(**终态**) | — |
| CREATED 待接单 | 关闭 CLOSE(撤单) | CLOSED 已关闭(**终态**) | — |
| ASSIGNED 处理中 | 超时(2h 未更新,每分钟扫描) | **不变更状态** | 降级为告警:生成 TIMEOUT_ALERT 事件 → 主管 E9001(T2);**不自动销毁**,见 §3.2-2 |
| PENDING_EXTERNAL 待外部 | 滞留(24h 未更新,每 30 分钟扫描) | **不变更状态** | 降级为催办:重新生成 PENDING_EXTERNAL 事件(T3);不自动销毁 |
| 任意状态 | 非法流转(状态机中不存在的边) | 拒绝 | 40900「非法状态流转:X -> Y」,工单不变 |
