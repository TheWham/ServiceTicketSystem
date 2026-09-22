-- 防止容器初始化时连接字符集为 latin1 导致中文乱码
SET NAMES utf8mb4;
-- ============================================================
-- user-service 种子数据:6 个用户,统一默认密码 123456(BCrypt)
-- ============================================================

USE it_user;

TRUNCATE TABLE ticket_draft;
TRUNCATE TABLE `user`;

INSERT INTO `user` (`user_id`, `name`, `role`, `department`, `phone`, `wechat_id`, `password_hash`) VALUES
('U001', '张小明', 'employee',   '市场部', '13800001001', 'zhangxm', '$2a$10$r6O5H5zxGln1pHqCJmp8ROvUOHSc8RcH24xt389XXc46ZSV6b.Dya'),
('U002', '李丽',   'employee',   '财务部', '13800001002', 'lily_li', '$2a$10$r6O5H5zxGln1pHqCJmp8ROvUOHSc8RcH24xt389XXc46ZSV6b.Dya'),
('U003', '王强',   'employee',   '研发部', '13800001003', 'wangqiang', '$2a$10$r6O5H5zxGln1pHqCJmp8ROvUOHSc8RcH24xt389XXc46ZSV6b.Dya'),
('U004', '赵工',   'engineer',   'IT部',   '13800002001', 'zhao_it', '$2a$10$r6O5H5zxGln1pHqCJmp8ROvUOHSc8RcH24xt389XXc46ZSV6b.Dya'),
('U005', '钱工',   'engineer',   'IT部',   '13800002002', 'qian_it', '$2a$10$r6O5H5zxGln1pHqCJmp8ROvUOHSc8RcH24xt389XXc46ZSV6b.Dya'),
('U006', '孙主管', 'supervisor', 'IT部',   '13800003001', 'sun_sup', '$2a$10$r6O5H5zxGln1pHqCJmp8ROvUOHSc8RcH24xt389XXc46ZSV6b.Dya');
