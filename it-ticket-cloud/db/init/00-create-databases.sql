-- ============================================================
-- IT 服务工单系统 · 微服务版建库脚本(Docker 初始化自动执行)
-- 数据库按服务拆分:user-service 拥有 it_user,ticket-service 拥有 it_ticket
-- ============================================================

CREATE DATABASE IF NOT EXISTS it_user
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS it_ticket
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
