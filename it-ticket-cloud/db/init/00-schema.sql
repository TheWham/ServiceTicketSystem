/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ai_interaction` (
  `interaction_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `session_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model_version` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `retrieved_versions` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '引用知识版本 JSON',
  `answer` text COLLATE utf8mb4_unicode_ci,
  `confidence` decimal(4,3) DEFAULT NULL,
  `refused` tinyint NOT NULL DEFAULT '0' COMMENT '拒答标记',
  `feedback` varchar(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HELPFUL/UNHELPFUL/WRONG',
  `latency` int DEFAULT NULL COMMENT '回答延迟(ms)',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`interaction_id`),
  KEY `idx_session` (`session_id`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI 回答记录（保存模型/来源/置信度/反馈 §17.2）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assignment` (
  `assignment_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `biz_type` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'CONSULTATION/TICKET',
  `biz_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `engineer_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `assigned_at` datetime NOT NULL,
  `response_deadline` datetime DEFAULT NULL COMMENT '响应 SLA 截止（10 工作分钟）',
  `responded_at` datetime DEFAULT NULL COMMENT '首次有效响应',
  `end_reason` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'RESPONDED/TIMEOUT_TRANSFER/TRANSFER_APPLY',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`assignment_id`),
  KEY `idx_engineer` (`engineer_id`,`assigned_at`),
  KEY `idx_biz` (`biz_type`,`biz_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分配记录（转派不删历史责任 §12.3）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `attachment` (
  `attachment_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `biz_type` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'CONSULTATION/TICKET',
  `biz_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `uploader_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `size` bigint NOT NULL COMMENT '≤20MB',
  `hash` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件哈希',
  `scan_status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/CLEAN/REJECTED',
  `withdrawn_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`attachment_id`),
  KEY `idx_biz` (`biz_type`,`biz_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='附件（先扫描后可用；保存哈希/上传人/扫描结果）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_log` (
  `audit_id` bigint NOT NULL AUTO_INCREMENT,
  `actor_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '操作人或 SYSTEM',
  `action` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `object_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `object_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `before_value` text COLLATE utf8mb4_unicode_ci,
  `after_value` text COLLATE utf8mb4_unicode_ci,
  `reason` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `request_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '请求追踪标识',
  `result` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'SUCCESS',
  `occurred_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`audit_id`),
  KEY `idx_object` (`object_type`,`object_id`,`occurred_at`),
  KEY `idx_actor` (`actor_id`,`occurred_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志（只追加；业务接口不得修改删除 §23）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `case_candidate` (
  `case_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_type` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'TICKET/CONSULTATION',
  `source_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `structured_content` text COLLATE utf8mb4_unicode_ci COMMENT '现象/范围/根因/步骤/验证/关键词/分类',
  `masking_status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/MASKED',
  `reusable_flag` tinyint NOT NULL DEFAULT '0' COMMENT '工程师标记复用价值',
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/PRIORITY/REVIEWED',
  `cluster_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`case_id`),
  KEY `idx_status` (`status`,`reusable_flag`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='案例池（COMPLETED 工单自动进入 §16.1）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `category` (
  `category_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `parent_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ticket_nature` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'INCIDENT/SERVICE_REQUEST',
  `name` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `level` tinyint NOT NULL COMMENT '1~3，仅末级可提单',
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ACTIVE',
  `version` int NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`category_id`),
  KEY `idx_parent` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分类（最多三级，停用保留快照）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `category_field_def` (
  `field_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `field_type` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'TEXT/RADIO/CHECKBOX/DATE/ATTACHMENT',
  `required` tinyint NOT NULL DEFAULT '0',
  `options` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '单选/多选值域 JSON',
  `sort_order` int NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`field_id`),
  KEY `idx_category` (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分类扩展字段（每末级分类最多 10 个）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `category_route` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `category_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `team_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `route_order` int NOT NULL COMMENT '有序候选团队',
  `effective_at` datetime NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_category_order` (`category_id`,`route_order`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分类路由（§12.1 分配算法第 1 步）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `consultation` (
  `session_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `creator_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '转人工前员工确认分类',
  `status` varchar(24) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'AI_ACTIVE' COMMENT 'AI_ACTIVE/WAITING_ENGINEER/HUMAN_ACTIVE/PENDING_CONFIRMATION/RESOLVED/CONVERTED_TO_TICKET/CLOSED',
  `current_engineer_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'AI' COMMENT 'AI/DIRECT_HUMAN',
  `resolved_type` varchar(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'CONFIRMED/AUTO',
  `auto_resolved` tinyint NOT NULL DEFAULT '0',
  `ticket_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '转工单后关联',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`session_id`),
  KEY `idx_creator` (`creator_id`,`created_at`),
  KEY `idx_engineer` (`current_engineer_id`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='咨询会话（与工单独立 §2.2）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `consultation_message` (
  `message_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `session_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sender_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sender_type` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'EMPLOYEE/ENGINEER/AI',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `withdrawn_at` datetime DEFAULT NULL COMMENT '撤回时间；不物理删除 §13.2',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`message_id`),
  KEY `idx_session_time` (`session_id`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='咨询消息（发送后不得编辑）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `engineer_status_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `engineer_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'AVAILABLE/BUSY/AWAY/OFFLINE',
  `source` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'MANUAL/AUTO',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_engineer_time` (`engineer_id`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工程师状态变更（须保留时间和来源 §6.2）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exception_queue` (
  `exception_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '异常单号',
  `biz_type` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'TICKET/CONSULTATION/NOTIFICATION',
  `biz_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '关联业务ID（工单/会话/通知）',
  `exception_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'NO_RESPONSE/ROUTE_FAILED/LONG_PENDING/NOTIFY_FAILED/LIMIT_EXCEEDED',
  `title` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '异常摘要',
  `detail` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '异常详情/原因',
  `priority` varchar(8) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '关联工单优先级',
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'OPEN' COMMENT 'OPEN/RESOLVED/DISMISSED',
  `resolved_by` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '处理人（平台管理员）',
  `resolved_at` datetime DEFAULT NULL,
  `resolution` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '处理结果说明（干预必须填原因 §18.2）',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`exception_id`),
  KEY `idx_status_type` (`status`,`exception_type`),
  KEY `idx_biz` (`biz_type`,`biz_id`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='异常队列（无人响应/路由失败/长期挂起/通知失败/超限 → 平台管理员处理）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `knowledge_article` (
  `article_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'DRAFT' COMMENT 'DRAFT/PENDING_REVIEW/PUBLISHED/OFFLINE（§16.3）',
  `current_version_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `risk_level` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'NORMAL' COMMENT 'NORMAL/HIGH（高风险须平台管理员复核 §16.4）',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`article_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识（不物理删除，只下线/新版本/回滚）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `knowledge_cluster` (
  `cluster_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `similarity_basis` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '类型/适用系统/现象/根因',
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/MERGED/SUSPECTED',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`cluster_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识簇（自动归簇不自动发布 §16.5）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `knowledge_version` (
  `version_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `article_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `version_no` int NOT NULL,
  `title` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `author_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `reviewer_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '审核人（不得自审 §16.4）',
  `recheck_by` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '高风险复核人（平台管理员）',
  `change_note` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `published_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`version_id`),
  KEY `idx_article` (`article_id`,`version_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识版本（新版本发布前旧版在线 §16.3）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notification` (
  `notification_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '领域事件实例 ID',
  `receiver_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `channel` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'INBOX/EMAIL',
  `dedup_key` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'event_id:receiver:channel（生命周期唯一 §14.3）',
  `title` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `content` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `action_url` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '待办行动入口（查看≠行动 §14.2）',
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/SENT/FAILED',
  `attempts` tinyint NOT NULL DEFAULT '0' COMMENT '站内重试 3 次；邮件指数退避',
  `last_error` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`notification_id`),
  UNIQUE KEY `uk_dedup` (`dedup_key`),
  KEY `idx_receiver` (`receiver_id`,`status`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知（幂等键唯一；最终失败入管理员异常记录）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sla_instance` (
  `sla_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ticket_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sla_type` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'RESPONSE/COMPLETION',
  `priority_snapshot` varchar(8) COLLATE utf8mb4_unicode_ci NOT NULL,
  `target_at` datetime DEFAULT NULL COMMENT '目标时刻（按工作时长推算）',
  `elapsed_work_seconds` bigint NOT NULL DEFAULT '0' COMMENT '累计有效工作秒',
  `paused_seconds` bigint NOT NULL DEFAULT '0',
  `near_breach_notified` tinyint NOT NULL DEFAULT '0' COMMENT '80% 提醒标记',
  `breach_at` datetime DEFAULT NULL COMMENT '违约时间（不可删除 §11.2）',
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'RUNNING' COMMENT 'RUNNING/PAUSED/STOPPED/BREACHED',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`sla_id`),
  KEY `idx_ticket` (`ticket_id`,`sla_type`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SLA 实例（完成 SLA 创建起算，验收阶段不消耗）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sla_pause` (
  `pause_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sla_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `reason_type` varchar(24) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'SUPPLEMENT/EXTERNAL',
  `started_at` datetime NOT NULL,
  `ended_at` datetime DEFAULT NULL,
  `operator_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`pause_id`),
  KEY `idx_sla` (`sla_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SLA 暂停（补充/外部等待期间暂停 §11.3）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `support_team` (
  `team_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ACTIVE',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`team_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='团队';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `team_member` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `team_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `engineer_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `joined_at` datetime NOT NULL,
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ACTIVE',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_engineer` (`engineer_id`),
  KEY `idx_team` (`team_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='团队成员';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ticket` (
  `ticket_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '工单编号',
  `creator_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nature` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'INCIDENT/SERVICE_REQUEST',
  `category_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '末级分类',
  `category_snapshot` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '分类快照（停用分类保留 §10.1）',
  `title` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '1~100 字符',
  `description` varchar(5000) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '10~5000 字符',
  `impact_description` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '影响情况（接单确认用）',
  `urgency_description` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '紧急说明',
  `location` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '本次联系方式，不反写身份源',
  `asset_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_check_status` varchar(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'PENDING/VERIFIED（CMDB 超时降级 §10.2）',
  `status` varchar(24) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'NEW' COMMENT 'NEW/ASSIGNED/IN_PROGRESS/PENDING_SUPPLEMENT/PENDING_EXTERNAL/PENDING_ACCEPTANCE/COMPLETED/CANCELLED/CLOSED',
  `priority` varchar(8) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'MEDIUM' COMMENT 'HIGH/MEDIUM/LOW（接单时按矩阵确认 §11.4）',
  `impact_scope` varchar(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '影响范围(接单矩阵输入):SINGLE/TEAM/DEPARTMENT/COMPANY',
  `urgency_level` varchar(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '紧急程度(接单矩阵输入):LOW/MEDIUM/HIGH/CRITICAL',
  `assignee_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_session_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '咨询转单来源',
  `auto_accepted` tinyint NOT NULL DEFAULT '0' COMMENT '48h 自动验收标记',
  `reopen_count` int NOT NULL DEFAULT '0',
  `idempotency_key` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '提单幂等键（§10.4）',
  `version` int NOT NULL DEFAULT '0' COMMENT '乐观锁',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `first_response_at` datetime DEFAULT NULL COMMENT '首次响应时间（工程师首次接单/回复，响应SLA判定）',
  `solved_at` datetime DEFAULT NULL COMMENT '解决时间（验收通过）',
  `rating_score` int DEFAULT NULL COMMENT '满意度评分 1-5',
  `rating_comment` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '评价内容',
  `rated_at` datetime DEFAULT NULL COMMENT '评价时间',
  PRIMARY KEY (`ticket_id`),
  KEY `idx_creator` (`creator_id`,`created_at`),
  KEY `idx_assignee_status` (`assignee_id`,`status`),
  KEY `idx_source_session` (`source_session_id`),
  KEY `idx_idem` (`creator_id`,`idempotency_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='正式工单主表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ticket_draft` (
  `draft_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nature` varchar(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'INCIDENT/REQUEST',
  `category_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `title` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `impact_description` text COLLATE utf8mb4_unicode_ci,
  `urgency_description` text COLLATE utf8mb4_unicode_ci,
  `location` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`draft_id`),
  KEY `idx_user` (`user_id`,`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='提单草稿(30s自动保存,PRD §10.5)';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ticket_field_value` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ticket_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `field_definition_snapshot` varchar(1000) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '提交时字段定义快照 §10.3',
  `field_value` varchar(2000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ticket` (`ticket_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工单扩展字段值（含定义快照）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ticket_message` (
  `message_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ticket_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sender_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `withdrawn_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`message_id`),
  KEY `idx_ticket_time` (`ticket_id`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工单聊天（当前双方可见 §13.1）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ticket_transition` (
  `transition_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ticket_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `from_status` varchar(24) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `to_status` varchar(24) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'SUBMIT/ROUTE/ACCEPT/SUPPLEMENT_REQUEST/...（§9.3）',
  `operator_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '含 SYSTEM',
  `reason` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '驳回/撤销/异常关闭必填',
  `occurred_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`transition_id`),
  KEY `idx_ticket_time` (`ticket_id`,`occurred_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工单流转（只追加，不覆盖 §2.2）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `user_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户标识',
  `employee_no` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '工号（身份源同步）',
  `name` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `department_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '部门（HR 同步）',
  `status` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ACTIVE' COMMENT 'ACTIVE/DISABLED',
  `identity_source` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'SSO',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `password_hash` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'BCrypt哈希(登录过渡用,非PRD字段,F-01 SSO上线后移除)',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_employee_no` (`employee_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户（员工不能在本系统改身份信息 §6.1）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_role` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role_code` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'EMPLOYEE/ENGINEER/PLATFORM_ADMIN/KB_ADMIN（§5.1 四角色）',
  `granted_by` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `granted_at` datetime NOT NULL,
  `revoked_at` datetime DEFAULT NULL COMMENT 'NULL=有效',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_role` (`user_id`,`role_code`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色授权（权限包独立授予，一人可多角色）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `work_calendar` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `cal_date` date NOT NULL,
  `day_type` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'WORKDAY/HOLIDAY',
  `start_time` time DEFAULT NULL COMMENT '默认 09:00',
  `end_time` time DEFAULT NULL COMMENT '默认 18:00',
  `lunch_pause` tinyint NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_date` (`cal_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='服务日历（节假日平台管理员维护）';
/*!40101 SET character_set_client = @saved_cs_client */;
