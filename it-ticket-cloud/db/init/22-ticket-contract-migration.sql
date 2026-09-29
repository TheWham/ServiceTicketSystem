-- ============================================================
-- 2026-09 新契约迁移(存量 it_ticket 库手工执行一次)
-- 内容:ticket 表新列(spec 05 TicketCreate / SQL-007)+ ticket_category
-- + ticket_draft + 分类种子。与 20-ticket-db.sql 尾部注释一致,可重复核对。
-- 幂等性:重复执行会因列已存在报错,属预期;新库请直接用 20/21 重建。
-- ============================================================

USE it_ticket;

-- 1. legacy 分类值统一(账号 → 账号权限,与 PRD 10.1 对齐)
--    顺序:先扩 ENUM 容纳新旧值 → 改数据 → 再收窄为最终值列表
ALTER TABLE `ticket`
  MODIFY COLUMN `category`
  ENUM('硬件','软件','网络','账号','账号权限','其他') NOT NULL COMMENT '问题分类';
UPDATE `ticket` SET category='账号权限' WHERE category='账号';

-- 2. ticket 表新列 + 列宽调整(先 NULL 加列,回填后再收紧 NOT NULL)
ALTER TABLE `ticket`
  MODIFY COLUMN `title` VARCHAR(100) NOT NULL COMMENT '工单标题 1-100字符',
  MODIFY COLUMN `description` TEXT NOT NULL COMMENT '问题描述 10-5000字符',
  MODIFY COLUMN `category` ENUM('硬件','软件','网络','账号权限','其他') NOT NULL
    COMMENT '分类名称(展示投影,来源 ticket_category.name)',
  MODIFY COLUMN `client_token` VARCHAR(128) DEFAULT NULL
    COMMENT '幂等防重 token(建单时取 Idempotency-Key,RD-002 上限 128)',
  ADD COLUMN `ticket_nature` VARCHAR(32) NULL
    COMMENT '工单性质 INCIDENT/SERVICE_REQUEST' AFTER `status`,
  ADD COLUMN `category_id` VARCHAR(64) NULL
    COMMENT '末级分类编号' AFTER `ticket_nature`,
  ADD COLUMN `impact_description` TEXT NULL
    COMMENT '影响情况' AFTER `category_id`,
  ADD COLUMN `urgency_description` TEXT NULL
    COMMENT '紧急说明' AFTER `impact_description`,
  ADD COLUMN `location` VARCHAR(255) NULL COMMENT '办公地点' AFTER `urgency_description`,
  ADD COLUMN `contact` VARCHAR(255) NULL COMMENT '本次联系方式' AFTER `location`,
  ADD COLUMN `source_session_id` VARCHAR(32) NULL
    COMMENT '来源咨询会话(CS 前缀,咨询转单时写入)' AFTER `client_token`,
  ADD COLUMN `field_snapshot_json` JSON NULL
    COMMENT '分类扩展字段值快照' AFTER `source_session_id`,
  ADD COLUMN `version` BIGINT NOT NULL DEFAULT 0
    COMMENT '乐观锁版本' AFTER `field_snapshot_json`,
  ADD INDEX `idx_source_session` (`source_session_id`);

-- 3. 回填历史行(保持 NOT NULL 约束)
UPDATE `ticket` SET
  ticket_nature = 'INCIDENT',
  category_id = CASE category
    WHEN '硬件' THEN 'CAT-HW'
    WHEN '软件' THEN 'CAT-SW'
    WHEN '网络' THEN 'CAT-NW'
    WHEN '账号权限' THEN 'CAT-ACCT'
    ELSE 'CAT-OTH' END,
  impact_description = IFNULL(impact_description, '（历史工单，未记录影响情况）'),
  urgency_description = IFNULL(urgency_description, '（历史工单，未记录紧急说明）');

ALTER TABLE `ticket`
  MODIFY COLUMN `ticket_nature` VARCHAR(32) NOT NULL COMMENT '工单性质 INCIDENT/SERVICE_REQUEST',
  MODIFY COLUMN `category_id` VARCHAR(64) NOT NULL COMMENT '末级分类编号',
  MODIFY COLUMN `impact_description` TEXT NOT NULL COMMENT '影响情况',
  MODIFY COLUMN `urgency_description` TEXT NOT NULL COMMENT '紧急说明';

-- 4. 分类表 + 种子(PRD 10.1:仅末级可提交工单)
CREATE TABLE IF NOT EXISTS `ticket_category` (
  `category_id` VARCHAR(64) NOT NULL COMMENT '末级分类编号',
  `name`        VARCHAR(100) NOT NULL COMMENT '分类名称(展示)',
  `enabled`     TINYINT(1) NOT NULL DEFAULT 1 COMMENT '平台管理员可停用;已有工单保留分类快照',
  `sort_no`     INT NOT NULL DEFAULT 0,
  `created_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`category_id`),
  INDEX `idx_enabled` (`enabled`, `sort_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单末级分类';

INSERT INTO `ticket_category` (`category_id`, `name`, `enabled`, `sort_no`) VALUES
('CAT-HW',   '硬件',    1, 1),
('CAT-SW',   '软件',    1, 2),
('CAT-NW',   '网络',    1, 3),
('CAT-ACCT', '账号权限', 1, 4),
('CAT-OTH',  '其他',    1, 5)
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`), `enabled` = 1;

-- 5. 提单草稿表(spec 05 saveTicketDraft / SQL-010:每员工一个活动草稿)
CREATE TABLE IF NOT EXISTS `ticket_draft` (
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
