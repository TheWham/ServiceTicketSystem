-- ============================================================
-- ticket-service 种子数据:5 个末级分类 + 3 张示例工单 + 流水
-- 2026-09 新契约:分类改为 ticket_category 表(PRD 10.1),
-- 工单补 ticket_nature/impact_description/urgency_description 必填列。
-- ============================================================

USE it_ticket;

TRUNCATE TABLE notification_log;
TRUNCATE TABLE ticket_flow_log;
TRUNCATE TABLE ticket_draft;
TRUNCATE TABLE ticket;
TRUNCATE TABLE ticket_category;

INSERT INTO `ticket_category` (`category_id`, `name`, `enabled`, `sort_no`) VALUES
('CAT-HW',   '硬件',    1, 1),
('CAT-SW',   '软件',    1, 2),
('CAT-NW',   '网络',    1, 3),
('CAT-ACCT', '账号权限', 1, 4),
('CAT-OTH',  '其他',    1, 5);

INSERT INTO `ticket`
  (`ticket_id`, `title`, `description`, `category`, `priority`, `status`,
   `ticket_nature`, `category_id`, `impact_description`, `urgency_description`, `location`, `contact`,
   `creator_id`, `assignee_id`, `first_response_at`, `created_at`) VALUES
('TK202609180001', '笔记本电脑无法开机', '今早到公司发现笔记本电脑按电源键无反应，电源灯不亮，已尝试插拔电源适配器无效。', '硬件', '高', '待处理',
  'INCIDENT', 'CAT-HW', '本人今日无法办公，无备用设备。', '业务中断，无替代方案。', '3 号楼 402', '张伟',
  'U001', NULL, '2026-09-18 08:30:00', '2026-09-18 08:30:00'),
('TK202609180002', 'VPN 连接失败', '从昨天下午开始 AnyConnect 一直报"无法建立连接"，已重启电脑和路由器均无效。', '网络', '中', '处理中',
  'INCIDENT', 'CAT-NW', '远程办公受阻，影响当日工作。', '有替代方案，可用手机热点临时办公。', NULL, '李娜',
  'U002', 'U004', '2026-09-18 09:05:00', '2026-09-18 09:00:00'),
('TK202609180003', 'ERP 系统无法登录', '登录 ERP 提示"账号已锁定"，需要解锁账号。', '账号', '高', '待验收',
  'INCIDENT', 'CAT-ACCT', '核心系统无法进入，部门当日报销流程停滞。', '核心系统受影响，业务中断。', NULL, '王强',
  'U003', 'U005', '2026-09-18 09:20:00', '2026-09-18 09:15:00');

INSERT INTO `ticket_flow_log` (`ticket_id`, `from_status`, `to_status`, `operator_id`, `remark`, `created_at`) VALUES
('TK202609180001', NULL, '待处理', 'U001', '提交工单', '2026-09-18 08:30:00'),
('TK202609180002', NULL, '待处理', 'U002', '提交工单', '2026-09-18 09:00:00'),
('TK202609180002', '待处理', '处理中', 'U006', '派单: 无', '2026-09-18 09:05:00'),
('TK202609180003', NULL, '待处理', 'U003', '提交工单', '2026-09-18 09:15:00'),
('TK202609180003', '待处理', '处理中', 'U006', '派单: 无', '2026-09-18 09:20:00'),
('TK202609180003', '处理中', '待验收', 'U005', '已重置密码，请尝试重新登录', '2026-09-18 09:40:00');
