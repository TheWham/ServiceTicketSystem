-- ============================================================================
-- V2_7__ticket_analytics_indexes.sql
-- ----------------------------------------------------------------------------
-- 跨工单聚合分析的取数索引。
--
-- 需求依据：
--   Day21「跨工单宏观聚合归纳」——分析链路的取数是按**时间窗**扫描 ticket 明细
--   （GET /api/internal/tickets/analytics/scan），谓词形如：
--       WHERE created_at >= ? AND created_at <= ?
--       ORDER BY created_at ASC, ticket_id ASC
--
-- 为什么必须新建索引：
--   ticket 表现有索引为
--     idx_ticket_creator_status(creator_id,status)
--     idx_ticket_assignee_status(assignee_id,status)
--     idx_ticket_priority_status(priority,status)
--     idx_ticket_title_category(title,category_id,created_at)
--     idx_ticket_source_session(source_session_id)
--   其中唯一含 created_at 的 idx_ticket_title_category **首列是 title**，
--   对「按时间窗过滤」完全用不上——MySQL 无法使用最左前缀之外的列做范围扫描，
--   结果是每次分析都退化成全表扫描。工单量随运营增长，这条索引是取数时效的前提。
--
-- 设计说明：
--   1. 复合列顺序 (created_at, ticket_id) 同时覆盖过滤与排序：过滤走首列，
--      ORDER BY created_at, ticket_id 可直接利用索引顺序，省掉一次 filesort。
--   2. 不加覆盖索引（不含 description/title）：投影要取的列里有 TEXT 大字段，
--      放进索引会让索引体积反超收益。
--   3. 与列表接口的既有索引不重叠，不改变任何现有查询的执行计划。
--
-- 幂等：MySQL 8 无 CREATE INDEX IF NOT EXISTS，故用 information_schema 存在性判断
--   加 PREPARE 动态执行。本迁移为纯增量，不含 DROP / TRUNCATE / DELETE；
--   重复执行时 @idx_exists > 0，动态语句退化为 SELECT 1（与 V2_6 同等执行契约）。
-- ============================================================================

SET @idx_exists := (
  SELECT COUNT(*)
  FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'ticket'
    AND index_name = 'idx_ticket_created_at'
);

SET @ddl := IF(
  @idx_exists = 0,
  'CREATE INDEX idx_ticket_created_at ON ticket (created_at, ticket_id)',
  'SELECT 1'
);

PREPARE analytics_idx_stmt FROM @ddl;
EXECUTE analytics_idx_stmt;
DEALLOCATE PREPARE analytics_idx_stmt;