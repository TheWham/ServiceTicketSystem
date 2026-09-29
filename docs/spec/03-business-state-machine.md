# 业务状态机流转矩阵

| 项目 | 约束 |
|---|---|
| 规范编号 | SM |
| 技术基线 | Java 17、Spring Boot 3.x；状态持久化类型引用 `DM-002` |
| 权威范围 | 咨询、工单、知识状态、事件、角色、守卫条件、迁移和业务副作用 |
| 数据引用 | 字段和实体见 `DM-*`；接口见 `AI-*`；失败处理见 `RD-*` |

本规范是业务状态合法性的唯一来源。它不定义数据库字段、HTTP JSON、重试次数、熔断阈值或存储实现。

## SM-001 迁移执行公约

- 每个迁移必须在事务内校验当前状态、操作者角色、对象归属和乐观锁版本。
- 合法迁移追加一个 `TicketTransition` 或等价审计事件，实体状态不可直接覆盖历史。
- 守卫失败返回 `ILLEGAL_STATE_TRANSITION`、`FORBIDDEN` 或 `ASSIGNMENT_CHANGED`；具体重试和降级引用 `RD-*`。
- 同一事件在同一对象上重复提交必须是幂等成功或返回明确的幂等冲突。
- 终态默认不可迁移；下表明确允许恢复的例外除外。
- 事件码使用稳定的 `DOMAIN_ACTION` 形式（例如 `TICKET_ACCEPT`、`CONSULTATION_TRANSFER`）；事件码一经发布不得复用为其他语义。
- 状态迁移先写主对象和不可变流转记录，再发布领域事件；通知、SLA、案例池和索引是副作用，不得反向决定迁移是否合法。
- 任何未列出的 `(当前状态, 事件, 角色)` 组合均拒绝，不允许客户端直接传入目标状态绕过动作白名单。

## SM-CONSULT-001 咨询状态

| 当前 | 事件 | 下一状态 | 角色 | 守卫条件 | 业务副作用 |
|---|---|---|---|---|---|
| 起点 | 开始 AI 咨询 | `AI_ACTIVE` | 员工 | 已登录 | 创建会话。 |
| 起点 | 跳过 AI 转人工 | `WAITING_ENGINEER` | 员工 | 已确认分类 | 创建人工分配任务。 |
| `AI_ACTIVE` | 转人工 | `WAITING_ENGINEER` | 员工 | 会话非终态 | 创建人工分配任务。 |
| `WAITING_ENGINEER` | 首次有效回复 | `HUMAN_ACTIVE` | 工程师 | 当前责任人；响应 SLA 未终止 | 记录响应时间。 |
| `HUMAN_ACTIVE` | 提交解决结论 | `PENDING_CONFIRMATION` | 工程师 | 结论非空 | 通知员工。 |
| `PENDING_CONFIRMATION` | 员工确认解决 | `RESOLVED` | 员工 | 结论已存在 | 生成案例候选入口。 |
| `PENDING_CONFIRMATION` | 断开且 10 分钟无回复 | `RESOLVED` | 系统 | 工程师已有结论，员工已断开 | 标记自动解决，通知员工。 |
| `PENDING_CONFIRMATION` | 员工回复未解决 | `HUMAN_ACTIVE` | 员工 | 内容非空 | 保留原结论。 |
| 任意非终态 | 确认创建工单 | `CONVERTED_TO_TICKET` | 员工 | 表单确认并提交成功 | 关联上下文和附件。 |
| 任意非终态 | 主动结束 | `CLOSED` | 员工 | 非强制处理场景 | 保存结束原因。 |
| `RESOLVED` | 24 小时内恢复 | `WAITING_ENGINEER` | 员工 | 未转工单，窗口未过期 | 重新启动人工响应 SLA。 |

`RESOLVED`、`CONVERTED_TO_TICKET`、`CLOSED` 为终态；仅 `RESOLVED` 允许 24 小时内恢复。

咨询规则补充：首次有效回复必须是工程师发送的实际消息，打开、已读或系统自动消息不计响应；AI 不可用时仍允许 `TRANSFER_TO_HUMAN` 或 `CREATE_TICKET`，不得把 AI 失败写成咨询终态。

## SM-TICKET-001 工单状态

| 当前 | 事件 | 下一状态 | 角色 | 守卫条件 | 业务副作用 |
|---|---|---|---|---|---|
| 起点 | 员工提交 | `NEW` | 员工 | 字段和幂等校验通过 | 创建工单、流转、SLA。 |
| `NEW` | 路由成功 | `ASSIGNED` | 系统 | 存在候选团队和工程师 | 记录响应截止时间，发通知。 |
| `NEW` | 无可用候选人 | `NEW` | 系统 | 所有候选团队不可用 | 进入异常队列并告警。 |
| `ASSIGNED` | 接单 | `IN_PROGRESS` | 当前工程师 | 响应 SLA 未过；确认影响和紧急程度 | 计算正式优先级，记录响应。 |
| `ASSIGNED` | 响应超时 | `ASSIGNED` | 系统 | 仍为当前责任人 | 记录违约，尝试下一候选人。 |
| `IN_PROGRESS` | 请求补充 | `PENDING_SUPPLEMENT` | 当前工程师 | 补充项非空 | 暂停完成 SLA，通知员工。 |
| `PENDING_SUPPLEMENT` | 提交补充 | `IN_PROGRESS` | 员工 | 补充文字或附件非空 | 恢复完成 SLA，通知工程师。 |
| `IN_PROGRESS` | 请求外部等待 | `PENDING_EXTERNAL` | 当前工程师 | 依赖、原因、预计时间齐全 | 暂停完成 SLA。 |
| `PENDING_EXTERNAL` | 外部恢复 | `IN_PROGRESS` | 当前工程师 | 恢复说明非空 | 恢复完成 SLA。 |
| `IN_PROGRESS` | 提交解决方案 | `PENDING_ACCEPTANCE` | 当前工程师 | 方案和验证结果非空 | 停止完成 SLA，通知员工。 |
| `PENDING_ACCEPTANCE` | 通过验收 | `COMPLETED` | 员工 | 无额外守卫 | 进入案例池。 |
| `PENDING_ACCEPTANCE` | 48 小时自动验收 | `COMPLETED` | 系统 | 员工未操作且计时到期 | 标记自动验收，进入案例池。 |
| `PENDING_ACCEPTANCE` | 驳回 | `IN_PROGRESS` | 员工 | 驳回原因非空 | 恢复剩余完成 SLA，通知工程师。 |
| 任意非终态 | 撤销 | `CANCELLED` | 员工 | 撤销原因非空 | 终止 SLA，通知当前责任人。 |
| `PENDING_SUPPLEMENT` | 72 小时未补充 | `CLOSED` | 系统 | 补充窗口到期 | 终止 SLA，记录关闭原因。 |
| 任意非终态 | 异常关闭 | `CLOSED` | 平台管理员 | 原因和二次确认齐全 | 终止 SLA，保留历史。 |
| 任意非终态 | 标记重复 | `CLOSED` | 平台管理员 | 已指定主工单 | 关联主工单，不合并私密数据。 |
| `COMPLETED` | 7 日内复发 | `IN_PROGRESS` | 员工 | 同一问题，复发说明非空 | 重新分配或原工程师继续。 |
| 特定 `CLOSED` | 规则允许恢复 | `IN_PROGRESS` | 员工/平台管理员 | 补充逾期或误判关闭 | 保留原历史，恢复处理。 |

`COMPLETED`、`CANCELLED`、`CLOSED` 为终态。`CANCELLED` 不允许恢复；`CLOSED` 只允许表中列出的原因恢复。

工单规则补充：`PENDING_ACCEPTANCE` 不消耗工程师完成 SLA；驳回返回 `IN_PROGRESS` 后从原累计有效耗时继续。原工程师继续负责的咨询转工单不重复启动响应 SLA，但完成 SLA 必须从正式建单时开始。

## SM-TICKET-002 优先级矩阵

工单创建时暂定 `MEDIUM`。工程师接单时确认两个事实维度，系统计算结果：

| 影响范围 \ 紧急程度 | 低 | 中 | 高 |
|---|---:|---:|---:|
| 单个员工 | LOW | LOW | MEDIUM |
| 多人或单部门 | LOW | MEDIUM | HIGH |
| 跨部门或核心系统 | MEDIUM | HIGH | HIGH |

平台管理员可修改优先级，但必须记录原因；新目标影响剩余 SLA，已消耗时间和违约不回滚。

## SM-TICKET-003 补充与外部等待守卫

- 补充最多发起 3 次；72 个自然小时未补充关闭，7 个自然日内可恢复。
- 外部等待每次必须有预计恢复时间；累计暂停超过 5 个工作日进入异常队列但不自动关闭。
- 外部审批证明属于员工补充材料，使用 `PENDING_SUPPLEMENT`，不创建审批状态。

## SM-KNOWLEDGE-001 知识状态

| 当前 | 事件 | 下一状态 | 角色 | 守卫 |
|---|---|---|---|---|
| `DRAFT` | 提交审核 | `PENDING_REVIEW` | 知识库管理员/工程师 | 已脱敏，结构化字段完整。 |
| `PENDING_REVIEW` | 审核通过 | `PUBLISHED` | 知识库管理员 | 作者不得自审；高风险须平台管理员复核。 |
| `PENDING_REVIEW` | 驳回 | `DRAFT` | 知识库管理员 | 必须有驳回原因。 |
| `PUBLISHED` | 下线 | `OFFLINE` | 知识库管理员 | 原因非空，刷新搜索和 RAG 索引。 |
| `PUBLISHED` | 新版本发布 | `PUBLISHED` | 知识库管理员 | 新版本审核完成后切换当前版本。 |
| `OFFLINE` | 新版本发布 | `PUBLISHED` | 知识库管理员 | 版本关联完整。 |

知识发布副作用：写入 `KNOWLEDGE_PUBLISHED` 或 `KNOWLEDGE_OFFLINE` 领域事实事件，要求刷新搜索和 RAG 索引；索引失败不回滚已经合法的知识状态，补偿规则引用 `RD-006` 和 `RD-008`。

## SM-EVENT-001 领域事件最小集合

| 状态机域 | 领域事实事件类型 `event_type` |
|---|---|
| 咨询 | `CONSULTATION_TRANSFERRED`、`CONSULTATION_RESPONDED`、`CONSULTATION_RESOLVED`、`CONSULTATION_REOPENED`、`CONSULTATION_CONVERTED` |
| 工单 | `TICKET_CREATED`、`TICKET_ASSIGNED`、`TICKET_RESPONDED`、`TICKET_STATUS_CHANGED`、`TICKET_PRIORITY_CHANGED`、`TICKET_TRANSFERRED`、`TICKET_REOPENED` |
| SLA | `SLA_NEAR_BREACH`、`SLA_BREACHED` |
| 知识 | `KNOWLEDGE_SUBMITTED`、`KNOWLEDGE_PUBLISHED`、`KNOWLEDGE_OFFLINE`、`KNOWLEDGE_INDEX_REFRESH_REQUESTED` |

领域事实事件的 `event_type` 统一使用 `SCREAMING_SNAKE_CASE`；状态迁移记录的 `eventCode` 是 `DOMAIN_ACTION` 业务动作码。事件载荷只携带对象 ID、领域事实事件类型、版本、操作者和发生时间；字段详情和持久化结构由 `DM-*` 负责，投递失败由 `RD-*` 负责。

## SM-ROLE-001 角色动作边界

- 员工只操作本人咨询和工单；
- 当前工程师只能操作当前责任对象；
- 历史工程师不可继续访问聊天或执行流转；
- 平台管理员可执行转派、优先级调整、异常关闭和符合规则的恢复；
- 知识库管理员只处理脱敏案例和知识版本；
- 任何角色不得物理删除消息、附件、流转或审计记录。
