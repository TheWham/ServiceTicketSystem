# PRD、Spec、API 与测试追踪矩阵

| 项目 | 约束 |
|---|---|
| 规范编号 | TR |
| 追踪源 | PRD 第 7、21、24、25、26 节 |
| 目标 | 每个功能/验收场景映射契约、接口、迁移和自动化测试 |

## TR-001 追踪规则

需求编号是不可变外键。测试名称必须包含 F-xx 或 AC-xx，报告保存 spec 编号、OpenAPI operationId、迁移版本和事件 ID。未在矩阵中的行为视为未获一期授权；重大变更先更新 PRD 和本矩阵。

## TR-002 功能追踪

| PRD 功能 | 主要契约 | API/事件入口 | 最低测试集 |
|---|---|---|---|
| F-01 身份组织 | AX-001/003、SQL、RD-006 | identity-sync、identity stream | SSO/HR 增量全量、禁用账号、失败快照、越权 |
| F-02 搜索咨询入口 | AI-005、SM-CONSULT、AX | AI-API-005、consultation read | AC-01/02、仅发布知识、越权 |
| F-03 转人工咨询 | 05、SM-CONSULT、EV、AX | consultation message/transfer | AC-03/04/05、响应 SLA、转派恢复 |
| F-04 咨询转工单 | 05、SQL、SM、RD-002 | ticket draft/create | AC-06、上下文关联、幂等 |
| F-05 直接提单草稿 | 05、SQL-005、RD-002 | ticket-draft/create | AC-07、草稿恢复、字段校验、并发 |
| F-06 路由负载转派 | SM、AX、RD-005 | accept/transfer/admin | AC-08/09/20/21、候选耗尽、责任收回 |
| F-07 工单处理验收 | 05、SM-TICKET、AX | tickets action endpoints | AC-10/12/13/14/15/16/17/18、非法状态 |
| F-08 SLA 提醒异常 | AX-002、EV、RD-004/008 | SLA scheduler、notification/exception stream | AC-11/12/13、暂停合并、重复扫描 |
| F-09 聊天撤回附件 | 05、DM-004、RD-009 | message/withdraw/attachment | AC-22/23、撤回窗口、真实 MIME、短期下载 |
| F-10 通知 | EV、RD-003/008 | notification stream | 幂等、邮件失败、DLQ 重放、站内兜底 |
| F-11 管理权限审计 | AX-001、SQL、RD-009 | admin-actions、audit view | AC-30、二次确认、追加审计、角色撤销 |
| F-12 案例知识 | 05、SM-KNOWLEDGE、EV | case/knowledge endpoints | AC-24/25/26/27、作者自审、相似聚类、索引补偿 |
| F-13 RAG/AI | AI-001~008、EV、RD-006 | AI-API-001~006 | AC-01/02/28/29、Schema、引用、拒答、降级 |

## TR-003 验收场景追踪

| 验收 | 测试标识 | 覆盖契约 |
|---|---|---|
| AC-01/02 | it.ai.answer_citation / refuse_without_source | AI-001/004/008、RD-006 |
| AC-03/04/05/06 | it.consultation.lifecycle | SM-CONSULT、05、AX-002 |
| AC-07/08/09 | it.ticket.idempotent_routing | RD-002/005、EV-002 |
| AC-10/11 | it.ticket.priority_sla | SM-TICKET-002、AX-002 |
| AC-12/13/14/15/16/17/18 | it.ticket.wait_accept_reopen | SM-TICKET-001/003、05、RD-004 |
| AC-19/20/21 | it.ticket.duplicate_transfer_privacy | AX-001、RD-005、SQL |
| AC-22/23 | it.message.withdraw_attachment_security | DM-004、05、RD-009 |
| AC-24/25/26/27/28 | it.knowledge.review_publish_index | SM-KNOWLEDGE、EV、RD-008 |
| AC-29 | it.dependency.degraded_mainline | AX-003/004、RD-006/007/013 |
| AC-30 | it.authz.object_scope_fuzz | AX-001、RD-009 |

## TR-004 非功能与发布门槛

| PRD 要求 | 验证方式 | 证据 |
|---|---|---|
| 95% 页面/API/AI 延迟 | 容量压测和 AI 首段/完整计时 | perf report，关联 operationId |
| 月可用性 99.9% | 监控和故障注入 | 仪表盘、告警记录 |
| RPO≤15 分钟/RTO≤2 小时 | 备份恢复演练 | 恢复报告、数据校验 |
| 高危漏洞清零 | SAST、依赖、附件、越权扫描 | 扫描归档 |
| 1B AI 门槛 | 代表性问题评测 | 评测集版本、引用/拒答指标 |

## TR-005 完成定义

某功能只有在 API 校验、MySQL 空库/旧库迁移、权限负例、状态非法、重复/并发、依赖故障、Outbox/Redis DLQ 重放、审计/指标/告警和对应 AC 全部有证据时才可标记完成。任何 AX-005 或 SQL-003 未决项冻结前，只允许开发桩和契约测试，不能宣称完成。


## TR-006 AC 独立追踪

每行测试均额外执行 TR-001 的通用维度：正常、权限/越权、非法状态、异常/超时、重试、幂等、并发、审计、通知和服务端校验。

| AC | 阶段 | Spec/API/Event/Table | 自动化测试 ID | Owner |
|---|---|---|---|---|
| AC-01 | 1B | AI-004/AI-API-002/ai_interaction | ac01_ai_citation | AI |
| AC-02 | 1B | AI-001/AI-API-002/RD-006 | ac02_ai_refusal | AI |
| AC-03 | 1A | SM-CONSULT-001/AI-API-004/CONSULTATION_TRANSFERRED/assignment | ac03_transfer_human | Consultation |
| AC-04 | 1A | SM-CONSULT-001/resolveConsultation/CONSULTATION_RESOLVED/consultation | ac04_human_resolve | Consultation |
| AC-05 | 1A | SM-CONSULT-001/reopenConsultation/CONSULTATION_REOPENED | ac05_consultation_reopen | Consultation |
| AC-06 | 1A | SM-CONSULT-001/createTicket/CONSULTATION_CONVERTED/ticket | ac06_convert_ticket | Ticket |
| AC-07 | 1A | RD-002/createTicket/TICKET_CREATED/idempotency_record | ac07_create_idempotent | Ticket |
| AC-08 | 1A | RD-005/TICKET_TRANSFERRED/assignment | ac08_response_timeout | Assignment |
| AC-09 | 1A | RD-005/SLA_BREACHED/exception_queue | ac09_candidate_exhausted | Assignment |
| AC-10 | 1A | SM-TICKET-002/acceptTicket/ticket | ac10_accept_priority | Ticket |
| AC-11 | 1A | AX-002/performTicketAdminAction/TICKET_PRIORITY_CHANGED/sla_instance | ac11_priority_sla | SLA |
| AC-12 | 1A | SM-TICKET-003/requestTicketSupplement/sla_pause | ac12_supplement_timeout | Ticket |
| AC-13 | 1A | SM-TICKET-003/startExternalWait/external_wait | ac13_external_wait | Ticket |
| AC-14 | 1A | SM-TICKET-001/submitTicketResolution/ticket_resolution | ac14_resolution | Ticket |
| AC-15 | 1A | SM-TICKET-001/acceptOrRejectTicket/ticket_acceptance | ac15_reject_acceptance | Ticket |
| AC-16 | 1A | SM-TICKET-001/TICKET_STATUS_CHANGED/ticket_acceptance | ac16_auto_accept | Ticket |
| AC-17 | 1A | SM-TICKET-001/performTicketAdminAction/TICKET_REOPENED | ac17_ticket_reopen | Ticket |
| AC-18 | 1A | SM-TICKET-001/cancelTicket/ticket_transition | ac18_cancel | Ticket |
| AC-19 | 1A | AX-001/performTicketAdminAction/ticket_duplicate | ac19_duplicate_privacy | Ticket |
| AC-20 | 1A | RD-005/requestTicketTransfer/TICKET_TRANSFERRED | ac20_engineer_transfer | Assignment |
| AC-21 | 1A | AX-001/TICKET_TRANSFERRED/assignment | ac21_chat_visibility | Authz |
| AC-22 | 1A | RD-009/withdrawMessage/ticket_message | ac22_withdraw | Messaging |
| AC-23 | 1A | RD-009/uploadAttachment/attachment | ac23_attachment_security | Attachment |
| AC-24 | 1A | SM-KNOWLEDGE-001/TICKET_STATUS_CHANGED/case_candidate | ac24_case_candidate | Knowledge |
| AC-25 | 1A | SM-KNOWLEDGE-001/reviewKnowledge/knowledge_version | ac25_no_self_review | Knowledge |
| AC-26 | 1A | PRD16/knowledge_cluster | ac26_similar_cluster | Knowledge |
| AC-27 | 1A/1B | SM-KNOWLEDGE-001/offlineKnowledge/KNOWLEDGE_OFFLINE | ac27_offline_index | Knowledge |
| AC-28 | 1B | AI-005/AI-API-003/ai_interaction | ac28_ai_feedback | AI |
| AC-29 | 1A/1B | RD-006/AX-003/createTicket | ac29_dependency_degrade | Platform |
| AC-30 | 1A | AX-001/getTicket/readWithdrawnMessageAudit | ac30_object_authz | Security |

## TR-007 补充非功能追踪

| 要求 | 自动化/证据 |
|---|---|
| 容量 1000 员工/50 工程师/200 在线 | nfr_capacity_1000_50_200 压测 |
| Chrome/Edge 最新及前两版、1366x768 | nfr_browser_matrix 截图与E2E |
| 手机/平板必要操作 | nfr_mobile_essential_actions E2E |
| 工单/咨询/聊天/附件及审计保留5年 | nfr_retention_5y 数据策略检查 |
| 普通访问日志180日、按月归档 | nfr_log_180d_monthly_archive |
| 每半年恢复，RPO/RTO | nfr_biannual_restore_drill |
| 上传实时进度和安全校验 | nfr_attachment_progress_security |

追踪主键使用 PRD version + requirement ID，例如 2.0/AC-01，避免后续 PRD 版本变更时编号歧义。
