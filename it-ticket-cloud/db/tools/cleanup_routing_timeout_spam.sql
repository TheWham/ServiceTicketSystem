-- ============================================================
-- 清理"响应超时转派"雪崩产生的垃圾数据
-- 背景:RoutingService 旧逻辑转派时只关闭最新一条 open assignment,
--       旧 open 记录被每分钟扫描反复命中,assignment / ticket_transition
--       膨胀到千万级,导致删工单超时、整库性能雪崩。
-- 前置:停掉所有 ticket-service 实例,确认 innodb_trx 无大事务在跑/回滚。
-- 用法:登录 it_ticket_system 库执行本脚本。执行完核对 *_cnt 后 drops。
-- ============================================================
USE it_ticket_system;

-- 1) 重建 ticket_transition:保留真实流转日志,剔除 TICKET_TIMEOUT_TRANSFER 垃圾
DROP TABLE IF EXISTS ticket_transition_new;
CREATE TABLE ticket_transition_new LIKE ticket_transition;
INSERT INTO ticket_transition_new
  SELECT * FROM ticket_transition WHERE event <> 'TICKET_TIMEOUT_TRANSFER';
SELECT
  (SELECT COUNT(*) FROM ticket_transition)      AS old_cnt,
  (SELECT COUNT(*) FROM ticket_transition_new)  AS new_cnt;
RENAME TABLE ticket_transition TO ticket_transition_old,
             ticket_transition_new TO ticket_transition;

-- 2) 重建 assignment:保留非工单业务行 + 正常关闭(非 TIMEOUT)的工单行,
--    剔除所有 open 垃圾与 TIMEOUT 关闭的转派垃圾
DROP TABLE IF EXISTS assignment_new;
CREATE TABLE assignment_new LIKE assignment;
INSERT INTO assignment_new
  SELECT * FROM assignment
  WHERE biz_type <> 'TICKET'
     OR (end_reason IS NOT NULL AND end_reason <> 'TIMEOUT');
SELECT
  (SELECT COUNT(*) FROM assignment)     AS old_cnt,
  (SELECT COUNT(*) FROM assignment_new) AS new_cnt;
RENAME TABLE assignment TO assignment_old,
             assignment_new TO assignment;

-- 3) 核对无误后删除旧表(约可释放十数 GB 磁盘)
-- DROP TABLE ticket_transition_old;
-- DROP TABLE assignment_old;
