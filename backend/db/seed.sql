-- ============================================================
-- IT 服务工单系统 · 种子数据 (P0 Mock)
-- ============================================================

USE it_ticket_system;

-- 清空测试数据
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE notification_log;
TRUNCATE TABLE ticket_flow_log;
TRUNCATE TABLE ticket_draft;
TRUNCATE TABLE ticket;
TRUNCATE TABLE user;
SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------
-- 用户 (3 种角色各 2-3 人)
-- ----------------------------
INSERT INTO `user` (`user_id`, `name`, `role`, `department`, `phone`, `wechat_id`) VALUES
('U001', '张小明', 'employee',   '市场部', '13800001001', 'zhangxm'),
('U002', '李丽',   'employee',   '财务部', '13800001002', 'lily_li'),
('U003', '王强',   'employee',   '研发部', '13800001003', 'wangqiang'),
('U004', '赵工',   'engineer',   'IT部',   '13800002001', 'zhao_it'),
('U005', '钱工',   'engineer',   'IT部',   '13800002002', 'qian_it'),
('U006', '孙主管', 'supervisor', 'IT部',   '13800003001', 'sun_sup');

-- ----------------------------
-- 示例工单(方便测试看板)
-- ----------------------------
INSERT INTO `ticket` (`ticket_id`, `title`, `description`, `category`, `priority`, `status`, `creator_id`, `assignee_id`, `created_at`) VALUES
('TK202609180001', '笔记本电脑无法开机', '今早到公司发现笔记本电脑按电源键无反应，电源灯不亮，已尝试插拔电源适配器无效。', '硬件', '高', '待处理', 'U001', NULL, '2026-09-18 08:30:00'),
('TK202609180002', 'VPN 连接失败', '从昨天下午开始 AnyConnect 一直报"无法建立连接"，已重启电脑和路由器均无效。', '网络', '中', '处理中', 'U002', 'U004', '2026-09-18 09:00:00'),
('TK202609180003', 'ERP 系统无法登录', '登录 ERP 提示"账号已锁定"，需要解锁账号。', '账号', '高', '待验收', 'U003', 'U005', '2026-09-18 09:15:00');

-- 示例流水
INSERT INTO `ticket_flow_log` (`ticket_id`, `from_status`, `to_status`, `operator_id`, `remark`, `created_at`) VALUES
('TK202609180001', NULL, '待处理', 'U001', '提交工单', '2026-09-18 08:30:00'),
('TK202609180002', NULL, '待处理', 'U002', '提交工单', '2026-09-18 09:00:00'),
('TK202609180002', '待处理', '处理中', 'U006', '分配给赵工处理', '2026-09-18 09:05:00'),
('TK202609180003', NULL, '待处理', 'U003', '提交工单', '2026-09-18 09:15:00'),
('TK202609180003', '待处理', '处理中', 'U006', '分配给钱工处理', '2026-09-18 09:20:00'),
('TK202609180003', '处理中', '待验收', 'U005', '已重置密码，请尝试重新登录', '2026-09-18 09:40:00');