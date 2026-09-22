-- ============================================================
-- IT 服务工单系统 · 数据库 Schema (P0 MVP)
-- 版本: v1.0 | 2026-09-18
-- ============================================================

CREATE DATABASE IF NOT EXISTS it_ticket_system
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE it_ticket_system;

-- ----------------------------
-- 1. 用户表 (员工/工程师/主管)
-- ----------------------------
CREATE TABLE `user` (
  `user_id`        VARCHAR(32)  NOT NULL COMMENT '用户ID，如 U001',
  `name`           VARCHAR(20)  NOT NULL COMMENT '姓名',
  `role`           ENUM('employee','engineer','supervisor') NOT NULL COMMENT '角色',
  `department`     VARCHAR(50)  DEFAULT NULL COMMENT '部门',
  `phone`          VARCHAR(20)  DEFAULT NULL COMMENT '手机号(短信兜底)',
  `wechat_id`      VARCHAR(50)  DEFAULT NULL COMMENT '企业微信ID',
  `status`         ENUM('active','inactive') DEFAULT 'active',
  `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  INDEX `idx_role` (`role`),
  INDEX `idx_department` (`department`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- ----------------------------
-- 2. 工单表 (核心实体)
-- ----------------------------
CREATE TABLE `ticket` (
  `ticket_id`           VARCHAR(32)  NOT NULL COMMENT '工单号 TK+yyyyMMdd+4位自增',
  `title`               VARCHAR(50)  NOT NULL COMMENT '工单标题(截取描述前50字)',
  `description`         VARCHAR(500) NOT NULL COMMENT '问题描述 10-500字符',
  `category`            ENUM('硬件','软件','网络','账号','其他') NOT NULL COMMENT '问题分类',
  `sub_category`        VARCHAR(20)  DEFAULT NULL COMMENT '二级分类(预留)',
  `priority`            ENUM('高','中','低') NOT NULL DEFAULT '中' COMMENT '优先级',
  `status`              ENUM('待处理','处理中','待补充','待外部','待验收','已完成','已取消') NOT NULL DEFAULT '待处理' COMMENT '工单状态',
  `creator_id`          VARCHAR(32)  NOT NULL COMMENT '提单人 user_id',
  `assignee_id`         VARCHAR(32)  DEFAULT NULL COMMENT '当前处理工程师 user_id',
  `asset_id`            VARCHAR(64)  DEFAULT NULL COMMENT '资产编号(预留CMDB联动)',
  `expected_finish_time` DATETIME    DEFAULT NULL COMMENT '期望完成时间',
  `attachment_urls`     JSON         DEFAULT NULL COMMENT '截图附件URL数组 ["url1","url2"]',
  `client_token`        VARCHAR(64)  DEFAULT NULL COMMENT '幂等防重 token',
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
  INDEX `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单表';

-- ----------------------------
-- 3. 状态流转日志表
-- ----------------------------
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

-- ----------------------------
-- 4. 通知记录表(幂等控制)
-- ----------------------------
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

-- ----------------------------
-- 5. 草稿表 (DOCX v5 特性)
-- ----------------------------
CREATE TABLE `ticket_draft` (
  `draft_id`        BIGINT       NOT NULL AUTO_INCREMENT,
  `user_id`         VARCHAR(32)  NOT NULL COMMENT '草稿归属人',
  `title`           VARCHAR(50)  DEFAULT NULL,
  `category`        VARCHAR(20)  DEFAULT NULL,
  `sub_category`    VARCHAR(20)  DEFAULT NULL,
  `priority`        VARCHAR(10)  DEFAULT '中',
  `description`     VARCHAR(500) DEFAULT NULL,
  `attachment_urls` JSON         DEFAULT NULL,
  `asset_id`        VARCHAR(64)  DEFAULT NULL,
  `expected_finish_time` DATETIME DEFAULT NULL,
  `updated_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`draft_id`),
  UNIQUE INDEX `uk_user_draft` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提单草稿表';