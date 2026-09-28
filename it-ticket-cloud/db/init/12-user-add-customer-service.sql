-- 防止容器初始化时连接字符集为 latin1 导致中文乱码
SET NAMES utf8mb4;
-- ============================================================
-- 新增角色:人工客服 customer_service,种子账号 U007(密码同其他种子:123456)
-- 说明:已初始化的环境(volume 已存在)请手动执行本脚本;
--      也可在业务运行期间重复执行(INSERT IGNORE 幂等)。
-- ============================================================

USE it_user;

INSERT IGNORE INTO `user` (`user_id`, `name`, `role`, `department`, `phone`, `wechat_id`, `password_hash`)
VALUES ('U007', '周客服', 'customer_service', 'IT部', '13800004001', 'zhou_cs',
        '$2a$10$r6O5H5zxGln1pHqCJmp8ROvUOHSc8RcH24xt389XXc46ZSV6b.Dya');
