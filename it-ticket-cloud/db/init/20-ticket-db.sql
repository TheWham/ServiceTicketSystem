-- ============================================================
-- ticket-service 库结构(it_ticket):工单 + 流转日志 + 通知记录
-- 与旧版 backend/db/schema.sql 完全一致
-- ============================================================

USE it_ticket;

-- 1. 工单表 (核心实体)
-- 2026-09 新契约升级(spec 05 TicketCreate / SQL-007):新增 ticket_nature/category_id/
-- impact_description/urgency_description/location/contact/field_snapshot_json/version;
-- 标题上限 100、描述上限 5000(app 层校验)。
-- legacy 列 category/priority(中文枚举值)保留为展示投影,供既有列表/看板直接使用。
CREATE TABLE `ticket` (
  `ticket_id`           VARCHAR(32)  NOT NULL COMMENT '工单号 TK+yyyyMMdd+4位自增',
  `title`               VARCHAR(100) NOT NULL COMMENT '工单标题 1-100字符',
  `description`         TEXT         NOT NULL COMMENT '问题描述 10-5000字符',
  `category`            ENUM('硬件','软件','网络','账号权限','其他') NOT NULL COMMENT '分类名称(展示投影,来源 ticket_category.name)',
  `sub_category`        VARCHAR(20)  DEFAULT NULL COMMENT '二级分类(预留)',
  `priority`            ENUM('高','中','低') NOT NULL DEFAULT '中' COMMENT '优先级(展示投影;新工单暂按中,PRD 11.4)',
  `status`              ENUM('待处理','处理中','待补充','待外部','待验收','已完成','已取消') NOT NULL DEFAULT '待处理' COMMENT '工单状态',
  `ticket_nature`       VARCHAR(32)  NOT NULL COMMENT '工单性质 INCIDENT/SERVICE_REQUEST(PRD 10.2)',
  `category_id`         VARCHAR(64)  NOT NULL COMMENT '末级分类编号(启用的末级分类,PRD 10.2)',
  `impact_description`  TEXT         NOT NULL COMMENT '影响情况 1-2000字符',
  `urgency_description` TEXT         NOT NULL COMMENT '紧急说明 1-2000字符',
  `location`            VARCHAR(255) DEFAULT NULL COMMENT '办公地点(选填)',
  `contact`             VARCHAR(255) DEFAULT NULL COMMENT '本次联系方式(默认来自身份源)',
  `creator_id`          VARCHAR(32)  NOT NULL COMMENT '提单人 user_id',
  `assignee_id`         VARCHAR(32)  DEFAULT NULL COMMENT '当前处理工程师 user_id',
  `asset_id`            VARCHAR(64)  DEFAULT NULL COMMENT '资产编号(预留CMDB联动)',
  `expected_finish_time` DATETIME    DEFAULT NULL COMMENT '期望完成时间(legacy,新契约不含)',
  `attachment_urls`     JSON         DEFAULT NULL COMMENT '截图附件URL数组 ["url1","url2"]',
  `client_token`        VARCHAR(128) DEFAULT NULL COMMENT '幂等防重 token(建单时取 Idempotency-Key,RD-002 上限 128)',
  `source_session_id`   VARCHAR(32)  DEFAULT NULL COMMENT '来源咨询会话(CS 前缀,咨询转单时写入)',
  `field_snapshot_json` JSON         DEFAULT NULL COMMENT '分类扩展字段值快照(field_values)',
  `version`             BIGINT       NOT NULL DEFAULT 0 COMMENT '乐观锁版本',
  `first_response_at`   DATETIME     DEFAULT NULL COMMENT '首次响应时间',
  `solved_at`           DATETIME     DEFAULT NULL COMMENT '解决关闭时间',
  `pause_minutes`       INT          DEFAULT 0  COMMENT '挂起累计暂停分钟数',
  `rating_score`        TINYINT      DEFAULT NULL COMMENT '满意度评分 1-5',
  `rating_comment`      VARCHAR(200) DEFAULT NULL COMMENT '评价文字',
  `rated_at`            DATETIME     DEFAULT NULL COMMENT '评价时间',
  `created_at`          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`ticket_id`),
  UNIQUE INDEX `uk_client_token` (`client_token`),
  INDEX `idx_status` (`status`),
  INDEX `idx_creator` (`creator_id`),
  INDEX `idx_assignee` (`assignee_id`),
  INDEX `idx_category` (`category`),
  INDEX `idx_priority` (`priority`),
  INDEX `idx_created` (`created_at`),
  INDEX `idx_source_session` (`source_session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单表';

-- 1b. 分类表(PRD 10.1:业务分类,仅末级可提交工单)
CREATE TABLE `ticket_category` (
  `category_id` VARCHAR(64) NOT NULL COMMENT '末级分类编号',
  `name`        VARCHAR(100) NOT NULL COMMENT '分类名称(展示)',
  `enabled`     TINYINT(1) NOT NULL DEFAULT 1 COMMENT '平台管理员可停用;已有工单保留分类快照',
  `sort_no`     INT NOT NULL DEFAULT 0,
  `created_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`category_id`),
  INDEX `idx_enabled` (`enabled`, `sort_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单末级分类';

-- 1c. 提单草稿表(spec 05 saveTicketDraft / SQL-010:每员工一个活动草稿)
CREATE TABLE `ticket_draft` (
  `draft_id`     VARCHAR(64) NOT NULL COMMENT '草稿编号(客户端持有,重登录可恢复)',
  `creator_id`   VARCHAR(32) NOT NULL COMMENT '所属员工',
  `payload_json` JSON        NOT NULL COMMENT '残缺字段也允许保存(PRD 10.4)',
  `last_saved_at` DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at`   DATETIME    NOT NULL COMMENT '过期时间,默认保存时刻 +7 天',
  `version`      BIGINT      NOT NULL DEFAULT 0,
  `created_at`   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`draft_id`),
  UNIQUE INDEX `uk_active_draft` (`creator_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提单草稿';

-- 2. 状态流转日志表
CREATE TABLE `ticket_flow_log` (
  `log_id`      BIGINT       NOT NULL AUTO_INCREMENT,
  `ticket_id`   VARCHAR(32)  NOT NULL COMMENT '工单号',
  `from_status` VARCHAR(20)  DEFAULT NULL COMMENT '变更前状态',
  `to_status`   VARCHAR(20)  NOT NULL COMMENT '变更后状态',
  `operator_id` VARCHAR(32)  NOT NULL COMMENT '操作人 user_id',
  `remark`      VARCHAR(500) DEFAULT NULL COMMENT '备注说明',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`log_id`),
  INDEX `idx_ticket_id` (`ticket_id`),
  INDEX `idx_operator` (`operator_id`),
  INDEX `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单流转日志';

-- 3. 通知记录表(幂等控制)
CREATE TABLE `notification_log` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT,
  `ticket_id`     VARCHAR(32)  NOT NULL,
  `event_type`    VARCHAR(50)  NOT NULL COMMENT '事件类型: SUBMIT_SUCCESS/DISPATCH/...',
  `receiver_id`   VARCHAR(32)  NOT NULL COMMENT '接收人 user_id',
  `channel`       ENUM('企微','短信','站内') NOT NULL DEFAULT '企微',
  `is_fallback`   TINYINT(1)   DEFAULT 0 COMMENT '是否兜底渠道',
  `delivery_status` ENUM('SUCCESS','FAILED','PENDING') DEFAULT 'PENDING',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_ticket_event` (`ticket_id`, `event_type`),
  INDEX `idx_receiver` (`receiver_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通知记录表';

-- 4. 已有环境增量迁移(数据已持久化、未重建库时手工执行一次):
--    ALTER TABLE `ticket`
--      MODIFY COLUMN `title` VARCHAR(100) NOT NULL COMMENT '工单标题 1-100字符',
--      MODIFY COLUMN `description` TEXT NOT NULL COMMENT '问题描述 10-5000字符',
--      MODIFY COLUMN `client_token` VARCHAR(128) DEFAULT NULL COMMENT '幂等防重 token',
--      ADD COLUMN `ticket_nature` VARCHAR(32) NOT NULL DEFAULT 'INCIDENT'
--        COMMENT '工单性质 INCIDENT/SERVICE_REQUEST' AFTER `status`,
--      ADD COLUMN `category_id` VARCHAR(64) NOT NULL DEFAULT 'CAT-OTH'
--        COMMENT '末级分类编号' AFTER `ticket_nature`,
--      ADD COLUMN `impact_description` TEXT NOT NULL
--        COMMENT '影响情况(legacy 行可置占位文本)' AFTER `category_id`,
--      ADD COLUMN `urgency_description` TEXT NOT NULL
--        COMMENT '紧急说明(legacy 行可置占位文本)' AFTER `impact_description`,
--      ADD COLUMN `location` VARCHAR(255) DEFAULT NULL AFTER `urgency_description`,
--      ADD COLUMN `contact` VARCHAR(255) DEFAULT NULL AFTER `location`,
--      ADD COLUMN `field_snapshot_json` JSON DEFAULT NULL AFTER `source_session_id`,
--      ADD COLUMN `version` BIGINT NOT NULL DEFAULT 0 AFTER `field_snapshot_json`,
--      ADD INDEX `idx_source_session` (`source_session_id`);
--    UPDATE `ticket` SET category='账号权限' WHERE category='账号';
--    ALTER TABLE `ticket` MODIFY COLUMN `category`
--      ENUM('硬件','软件','网络','账号权限','其他') NOT NULL COMMENT '分类名称(展示投影)';
--    UPDATE `ticket` SET impact_description='(历史工单,未记录)', urgency_description='(历史工单,未记录)';
--    CREATE TABLE ticket_category / ticket_draft:见上方 1b/1c 建表语句。
