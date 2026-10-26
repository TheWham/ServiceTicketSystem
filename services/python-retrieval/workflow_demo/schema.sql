-- workflow_demo 本地种子库（SQLite）
--
-- 表结构与数据刻意照抄项目的真实事实源，只做 MySQL→SQLite 的语法降级：
--   it-ticket-cloud/db/init/*.sql（分类、分类路由、支持组、用户）
--   docs/IT服务工单系统PRD-Ultimate.md 11.2/11.3（SLA 目标值）
--   .agents/skills/ai-agent-guard、agent_service/prompts（敏感操作口径）
--
-- 未引入向量库：本 demo 演示的是「编排 + 观测」，不是检索质量；关键词匹配足够。

DROP TABLE IF EXISTS category;
CREATE TABLE category (
    category_id VARCHAR(64) PRIMARY KEY,
    parent_id   VARCHAR(64),
    name        VARCHAR(255) NOT NULL,
    status      VARCHAR(32)  NOT NULL
);

DROP TABLE IF EXISTS support_team;
CREATE TABLE support_team (
    team_id VARCHAR(64) PRIMARY KEY,
    name    VARCHAR(255) NOT NULL,
    status  VARCHAR(32)  NOT NULL
);

-- 决策表：分类 → 支持组（真实系统里由管理员维护，改一行即热更新，无需重建知识库）
DROP TABLE IF EXISTS category_route;
CREATE TABLE category_route (
    category_id VARCHAR(64) NOT NULL,
    team_id     VARCHAR(64) NOT NULL,
    route_order INTEGER     NOT NULL,
    PRIMARY KEY (category_id, team_id)
);

-- 决策表：优先级 → SLA 目标（PRD 11.2 / 11.3）
DROP TABLE IF EXISTS sla_target;
CREATE TABLE sla_target (
    priority                   VARCHAR(32) PRIMARY KEY,
    response_target_seconds    INTEGER NOT NULL,  -- 响应 SLA：10 个工作分钟
    completion_target_seconds  INTEGER NOT NULL   -- 完成 SLA：HIGH 4h / MEDIUM 1d / LOW 3d
);

-- 服务日历（PRD 11.1）：周一至周五 09:00~18:00，午休 12:00~13:00 不计入
DROP TABLE IF EXISTS service_calendar;
CREATE TABLE service_calendar (
    calendar_id   VARCHAR(64) PRIMARY KEY,
    work_week     VARCHAR(32) NOT NULL,   -- 1=周一 ... 7=周日
    work_start    VARCHAR(8)  NOT NULL,
    work_end      VARCHAR(8)  NOT NULL,
    lunch_start   VARCHAR(8)  NOT NULL,
    lunch_end     VARCHAR(8)  NOT NULL,
    workday_seconds INTEGER   NOT NULL    -- 单个工作日的有效工作时长（秒）
);

DROP TABLE IF EXISTS app_user;
CREATE TABLE app_user (
    user_id     VARCHAR(64) PRIMARY KEY,
    employee_no VARCHAR(64) NOT NULL,
    name        VARCHAR(255) NOT NULL,
    role_code   VARCHAR(32)  NOT NULL
);

DROP TABLE IF EXISTS knowledge_article;
CREATE TABLE knowledge_article (
    article_id         VARCHAR(64) PRIMARY KEY,
    status             VARCHAR(32) NOT NULL,   -- PUBLISHED | OFFLINE
    current_version_id VARCHAR(64) NOT NULL,
    category_id        VARCHAR(64) NOT NULL,
    risk_level         VARCHAR(32) NOT NULL
);

DROP TABLE IF EXISTS knowledge_version;
CREATE TABLE knowledge_version (
    version_id  VARCHAR(64) PRIMARY KEY,
    article_id  VARCHAR(64) NOT NULL,
    version_no  INTEGER     NOT NULL,
    title       VARCHAR(255) NOT NULL,
    summary     TEXT        NOT NULL,
    keywords    TEXT        NOT NULL,
    body        TEXT        NOT NULL
);

DROP TABLE IF EXISTS ticket;
CREATE TABLE ticket (
    ticket_id   VARCHAR(32) PRIMARY KEY,
    creator_id  VARCHAR(64) NOT NULL,
    category_id VARCHAR(64) NOT NULL,
    title       VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    status      VARCHAR(32) NOT NULL,
    priority    VARCHAR(32) NOT NULL,
    assignee_id VARCHAR(64),
    created_at  TEXT NOT NULL
);

-- ============================ 种子数据 ============================

-- 分类（照抄项目种子）
INSERT INTO category (category_id, parent_id, name, status) VALUES
('C_HW',    NULL,   '硬件',           'ACTIVE'),
('C_HW_PC', 'C_HW', '台式机/笔记本',  'ACTIVE'),
('C_HW_PR', 'C_HW', '打印机/外设',    'ACTIVE'),
('C_SW',    NULL,   '软件',           'ACTIVE'),
('C_NET',   NULL,   '网络',           'ACTIVE'),
('C_ACC',   NULL,   '账号权限',       'ACTIVE'),
('C_OTH',   NULL,   '其他',           'ACTIVE');

-- 支持组（照抄项目种子）
INSERT INTO support_team (team_id, name, status) VALUES
('T_HW',  '硬件支持组', 'ACTIVE'),
('T_SW',  '软件支持组', 'ACTIVE'),
('T_NET', '网络支持组', 'ACTIVE');

-- 分类路由决策表（照抄项目种子）
INSERT INTO category_route (category_id, team_id, route_order) VALUES
('C_HW_PC', 'T_HW',  1),
('C_HW_PR', 'T_HW',  1),
('C_SW',    'T_SW',  1),
('C_NET',   'T_NET', 1),
('C_ACC',   'T_SW',  1),
('C_OTH',   'T_HW',  1);

-- SLA 目标（PRD 11.2 响应 10 个工作分钟；11.3 完成 HIGH 4 工作小时 / MEDIUM 1 工作日 / LOW 3 工作日）
-- 一个工作日 = 8 工作小时 = 28800 秒
INSERT INTO sla_target (priority, response_target_seconds, completion_target_seconds) VALUES
('HIGH',   600, 14400),
('MEDIUM', 600, 28800),
('LOW',    600, 86400);

-- 服务日历（PRD 11.1）
INSERT INTO service_calendar (calendar_id, work_week, work_start, work_end, lunch_start, lunch_end, workday_seconds) VALUES
('DEFAULT', '1,2,3,4,5', '09:00', '18:00', '12:00', '13:00', 28800);

-- 用户（照抄项目种子）
INSERT INTO app_user (user_id, employee_no, name, role_code) VALUES
('U_EMP01', 'E1001', '演示员工',   'EMPLOYEE'),
('U_ENG01', 'E2001', '演示工程师', 'ENGINEER'),
('U_ADM01', 'E3001', '平台管理员', 'PLATFORM_ADMIN');

-- 知识库（照抄项目种子）
-- 注意：KA-VPN-CONNECT 保留 v1 旧版 + v2 现行版本，用于验证「只返回当前版本」；
--       KA-OLD-MAIL 为 OFFLINE，用于验证「已下线文章不得召回」（AC-27 / RD-006）。
INSERT INTO knowledge_article (article_id, status, current_version_id, category_id, risk_level) VALUES
('KA-PRINTER-OFFLINE', 'PUBLISHED', 'KV-PRINTER-OFFLINE-1', 'C_HW_PR', 'NORMAL'),
('KA-VPN-CONNECT',     'PUBLISHED', 'KV-VPN-CONNECT-2',     'C_NET',   'NORMAL'),
('KA-WIFI-SLOW',       'PUBLISHED', 'KV-WIFI-SLOW-1',       'C_NET',   'NORMAL'),
('KA-OLD-MAIL',        'OFFLINE',   'KV-OLD-MAIL-1',        'C_ACC',   'NORMAL');

INSERT INTO knowledge_version (version_id, article_id, version_no, title, summary, keywords, body) VALUES
('KV-PRINTER-OFFLINE-1', 'KA-PRINTER-OFFLINE', 1,
 '打印机显示离线的排查步骤',
 '打印机离线多数由网络断开、驱动异常或队列卡死引起，按顺序排查可自助恢复。',
 '打印机 离线 无法打印 队列 驱动',
 '1. 确认打印机电源与网线/无线指示灯正常。2. 在系统设置中删除卡住的打印队列任务。3. 重启打印后台处理程序服务。4. 若仍离线，重新安装厂商驱动。5. 以上无效请转人工或提交工单，注明打印机资产编号。'),

('KV-VPN-CONNECT-1', 'KA-VPN-CONNECT', 1,
 'VPN 无法连接（旧版）',
 '旧版步骤，已被 v2 取代。',
 'VPN 连接',
 '旧版内容。'),

('KV-VPN-CONNECT-2', 'KA-VPN-CONNECT', 2,
 'VPN 无法连接的排查步骤',
 'VPN 连接失败常见于客户端版本过旧、本地网络受限或账号未开通 VPN 权限。',
 'VPN 无法连接 拨号 超时 远程办公',
 '1. 确认客户端为公司发布的最新版本。2. 切换到手机热点排除本地网络限制。3. 确认账号已开通 VPN 权限，未开通需走权限申请。4. 记录错误码后转人工。'),

('KV-WIFI-SLOW-1', 'KA-WIFI-SLOW', 1,
 '办公室 WiFi 速度慢的处理方式',
 'WiFi 变慢通常与信道拥塞、终端过多或距离过远有关。',
 'WiFi 无线 网速慢 卡顿',
 '1. 优先连接 5GHz 频段。2. 靠近 AP 覆盖区域。3. 关闭后台大流量应用。4. 持续变慢请转人工并提供工位号。'),

('KV-OLD-MAIL-1', 'KA-OLD-MAIL', 1,
 '旧邮箱迁移说明',
 '该流程已下线。',
 '邮箱 迁移',
 '已废弃的迁移步骤。');

-- 工单（时间相对「现在」生成，保证重复单窗口永远有效）
-- U_EMP01 名下一张 2 小时前提交、仍在处理的打印机工单 → 用于触发重复单拦截
INSERT INTO ticket (ticket_id, creator_id, category_id, title, description, status, priority, assignee_id, created_at) VALUES
('T20260115-001', 'U_EMP01', 'C_HW_PR', '办公室打印机显示离线',
 '打印机面板显示离线，无法打印，已重启过打印机。', 'IN_PROGRESS', 'MEDIUM', 'U_ENG01', datetime('now', '-2 hours')),
('T20260115-002', 'U_EMP01', 'C_NET', 'VPN 连接超时',
 '在家办公 VPN 拨号超时，错误码 691。', 'ASSIGNED', 'HIGH', 'U_ENG01', datetime('now', '-1 day')),
('T20251220-007', 'U_EMP01', 'C_HW_PC', '笔记本无法开机',
 '按电源键无反应，已更换电源适配器仍无效。', 'CLOSED', 'HIGH', 'U_ENG01', datetime('now', '-30 days'));