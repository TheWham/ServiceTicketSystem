-- ============================================================
-- user-service 库结构(it_user):用户表 + 提单草稿表
-- 与旧版 backend/db/schema.sql 一致,新增 password_hash 列(JWT 登录)
-- ============================================================

USE it_user;

-- 1. 用户表 (员工/工程师/主管)
CREATE TABLE `user` (
  `user_id`        VARCHAR(32)  NOT NULL COMMENT '用户ID，如 U001',
  `name`           VARCHAR(20)  NOT NULL COMMENT '姓名',
  `role`           ENUM('employee','engineer','supervisor') NOT NULL COMMENT '角色',
  `department`     VARCHAR(50)  DEFAULT NULL COMMENT '部门',
  `phone`          VARCHAR(20)  DEFAULT NULL COMMENT '手机号(短信兜底)',
  `wechat_id`      VARCHAR(50)  DEFAULT NULL COMMENT '企业微信ID',
  `password_hash`  VARCHAR(100) NOT NULL DEFAULT '' COMMENT 'BCrypt 密码哈希',
  `status`         ENUM('active','inactive') DEFAULT 'active',
  `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  INDEX `idx_role` (`role`),
  INDEX `idx_department` (`department`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 2. 草稿表
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
