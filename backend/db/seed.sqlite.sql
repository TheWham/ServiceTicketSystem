-- ============================================================
-- IT 服务工单系统 · 种子数据 (SQLite)
-- ============================================================

DELETE FROM notification_log;
DELETE FROM ticket_flow_log;
DELETE FROM ticket_draft;
DELETE FROM ticket;
DELETE FROM asset;
DELETE FROM user;

-- ----------------------------
-- 用户 (3 种角色)
-- ----------------------------
INSERT INTO user (user_id, name, role, department, phone, wechat_id) VALUES
('U001', '张小明', 'employee',   '市场部', '13800001001', 'zhangxm'),
('U002', '李丽',   'employee',   '财务部', '13800001002', 'lily_li'),
('U003', '王强',   'employee',   '研发部', '13800001003', 'wangqiang'),
('U004', '赵工',   'engineer',   'IT部',   '13800002001', 'zhao_it'),
('U005', '钱工',   'engineer',   'IT部',   '13800002002', 'qian_it'),
('U006', '孙主管', 'supervisor', 'IT部',   '13800003001', 'sun_sup');

-- ----------------------------
-- 资产 (owner_id 关联 user.user_id)
-- ----------------------------
INSERT INTO asset (asset_id, model, owner_id, status) VALUES
('IT-PC-20260901', 'ThinkPad X1 Carbon', 'U001', '在用'),
('IT-PC-20260902', 'Dell Latitude 5420',  'U002', '在用'),
('IT-MB-20260815', 'MacBook Pro 14',      'U003', '在用'),
('IT-PC-20250110', 'HP EliteBook 840',    NULL,   '维修');

-- ----------------------------
-- 示例工单 (方便测试看板)
-- ----------------------------
INSERT INTO ticket (ticket_id, title, description, category, priority, status, creator_id, assignee_id, created_at) VALUES
('TK202609180001', '笔记本电脑无法开机', '今早到公司发现笔记本电脑按电源键无反应，电源灯不亮，已尝试插拔电源适配器无效。', '硬件', '高', '待处理', 'U001', NULL, '2026-09-18 08:30:00'),
('TK202609180002', 'VPN 连接失败', '从昨天下午开始 AnyConnect 一直报"无法建立连接"，已重启电脑和路由器均无效。', '网络', '中', '处理中', 'U002', 'U004', '2026-09-18 09:00:00'),
('TK202609180003', 'ERP 系统无法登录', '登录 ERP 提示"账号已锁定"，需要解锁账号。', '账号', '高', '待验收', 'U003', 'U005', '2026-09-18 09:15:00');

-- ----------------------------
-- 示例流转日志
-- ----------------------------
INSERT INTO ticket_flow_log (ticket_id, from_status, to_status, operator_id, remark, created_at) VALUES
('TK202609180001', NULL, '待处理', 'U001', '提交工单', '2026-09-18 08:30:00'),
('TK202609180002', NULL, '待处理', 'U002', '提交工单', '2026-09-18 09:00:00'),
('TK202609180002', '待处理', '处理中', 'U006', '分配给赵工处理', '2026-09-18 09:05:00'),
('TK202609180003', NULL, '待处理', 'U003', '提交工单', '2026-09-18 09:15:00'),
('TK202609180003', '待处理', '处理中', 'U006', '分配给钱工处理', '2026-09-18 09:20:00'),
('TK202609180003', '处理中', '待验收', 'U005', '已重置密码，请尝试重新登录', '2026-09-18 09:40:00');
