-- ============================================================
-- consultation-service 种子数据(it_consultation)
-- 目的:让「智能客服 + 转人工」在本地一键跑通。
-- 工程师 ID 与 it_user 的种子对齐:U004 赵工、U005 钱工(role=engineer)。
-- 时间列一律 UTC(应用口径),UTC_TIMESTAMP(6) 与之一致。
-- ============================================================

USE it_consultation;

-- 只清空配置与知识投影,不动咨询事实表(审计与消息只追加,不允许 TRUNCATE)
TRUNCATE TABLE knowledge_version;
TRUNCATE TABLE knowledge_article;
TRUNCATE TABLE engineer_category_capability;
TRUNCATE TABLE engineer_runtime_state;
TRUNCATE TABLE category_route;
TRUNCATE TABLE team_member;
TRUNCATE TABLE support_team;
TRUNCATE TABLE category;
TRUNCATE TABLE calendar_holiday;
TRUNCATE TABLE service_calendar;

-- ---------- 服务日历(PRD 11.1:周一至周五 09:00-18:00,午休可配置暂停) ----------
INSERT INTO service_calendar
  (calendar_id, timezone, work_week_json, work_intervals_json, lunch_pauses,
   version, effective_from, created_at, updated_at)
VALUES
  ('DEFAULT', 'Asia/Shanghai', '[1,2,3,4,5]',
   '[{"start":"09:00","end":"12:00"},{"start":"13:00","end":"18:00"}]', 1,
   1, '2026-01-01 00:00:00.000000', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6));

INSERT INTO calendar_holiday (holiday_id, calendar_id, holiday_date, name, is_working_day) VALUES
  ('HOL-20261001', 'DEFAULT', '2026-10-01', '国庆节', 0),
  ('HOL-20261002', 'DEFAULT', '2026-10-02', '国庆节', 0),
  ('HOL-20261010', 'DEFAULT', '2026-10-10', '国庆调休补班', 1);

-- ---------- 分类(一期两级:一级域 + 末级可路由分类) ----------
INSERT INTO category
  (category_id, parent_id, nature, name, level, definition_version, enabled, version, created_at, updated_at)
VALUES
  ('CAT-IT',         NULL,     'INCIDENT',        'IT 支持',   1, 'v1', 1, 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('CAT-IT-DEVICE',  'CAT-IT', 'INCIDENT',        '办公设备',  2, 'v1', 1, 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('CAT-IT-NETWORK', 'CAT-IT', 'INCIDENT',        '网络访问',  2, 'v1', 1, 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('CAT-IT-ACCOUNT', 'CAT-IT', 'SERVICE_REQUEST', '账号与权限', 2, 'v1', 1, 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6));

-- ---------- 支持团队与成员 ----------
INSERT INTO support_team (team_id, name, enabled, version, created_at, updated_at) VALUES
  ('TEAM-DESKTOP', '桌面支持组', 1, 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('TEAM-NETWORK', '网络支持组', 1, 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6));

INSERT INTO team_member (team_id, engineer_id, joined_at, left_at, enabled, created_at, updated_at) VALUES
  ('TEAM-DESKTOP', 'U004', '2026-01-01 00:00:00.000000', NULL, 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('TEAM-DESKTOP', 'U005', '2026-01-01 00:00:00.000000', NULL, 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('TEAM-NETWORK', 'U005', '2026-01-01 00:00:00.000000', NULL, 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6));

-- ---------- 分类路由(PRD 12.1:按 route_order 形成有序候选团队) ----------
INSERT INTO category_route
  (category_id, team_id, route_order, effective_at, expired_at, created_at, updated_at)
VALUES
  ('CAT-IT-DEVICE',  'TEAM-DESKTOP', 1, '2026-01-01 00:00:00.000000', NULL, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('CAT-IT-NETWORK', 'TEAM-NETWORK', 1, '2026-01-01 00:00:00.000000', NULL, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('CAT-IT-NETWORK', 'TEAM-DESKTOP', 2, '2026-01-01 00:00:00.000000', NULL, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('CAT-IT-ACCOUNT', 'TEAM-DESKTOP', 1, '2026-01-01 00:00:00.000000', NULL, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6));

-- 不写 engineer_category_capability:团队未做分类细分时,团队路由本身即代表可接该分类。

-- ---------- 工程师在线状态(PRD 6.2:只有 AVAILABLE 可分配新咨询) ----------
INSERT INTO engineer_runtime_state
  (engineer_id, presence, last_activity_at, last_assigned_at, version, created_at, updated_at)
VALUES
  ('U004', 'AVAILABLE', UTC_TIMESTAMP(6), NULL, 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('U005', 'AVAILABLE', UTC_TIMESTAMP(6), NULL, 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6));

-- ---------- 已发布知识(AI 与知识搜索的唯一数据来源) ----------
INSERT INTO knowledge_article
  (article_id, status, current_version_id, category_id, risk_level, version, created_at, updated_at)
VALUES
  ('KA-PRINTER-OFFLINE', 'PUBLISHED', 'KV-PRINTER-OFFLINE-1', 'CAT-IT-DEVICE',  'NORMAL', 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('KA-VPN-CONNECT',     'PUBLISHED', 'KV-VPN-CONNECT-2',     'CAT-IT-NETWORK', 'NORMAL', 2, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('KA-WIFI-SLOW',       'PUBLISHED', 'KV-WIFI-SLOW-1',       'CAT-IT-NETWORK', 'NORMAL', 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  -- 已下线文章:用于验证 AI 与搜索都不得返回它(AC-27、RD-006)
  ('KA-OLD-MAIL',        'OFFLINE',   'KV-OLD-MAIL-1',        'CAT-IT-ACCOUNT', 'NORMAL', 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6));

INSERT INTO knowledge_version
  (version_id, article_id, version_no, content_json, author_id, reviewer_id, published_at, change_note, created_at, updated_at)
VALUES
  ('KV-PRINTER-OFFLINE-1', 'KA-PRINTER-OFFLINE', 1,
   JSON_OBJECT(
     'title', '打印机显示离线的排查步骤',
     'summary', '打印机离线多数由网络断开、驱动异常或队列卡死引起,按顺序排查可自助恢复。',
     'keywords', '打印机 离线 无法打印 队列 驱动',
     'body', '1. 确认打印机电源与网线/无线指示灯正常。2. 在系统设置中删除卡住的打印队列任务。3. 重启打印后台处理程序服务。4. 若仍离线,重新安装厂商驱动。5. 以上无效请转人工或提交工单,注明打印机资产编号。'),
   'U004', 'U006', UTC_TIMESTAMP(6), '首次发布', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),

  ('KV-VPN-CONNECT-1', 'KA-VPN-CONNECT', 1,
   JSON_OBJECT('title', 'VPN 无法连接(旧版)', 'summary', '旧版步骤,已被 v2 取代。',
               'keywords', 'VPN 连接', 'body', '旧版内容。'),
   'U004', 'U006', UTC_TIMESTAMP(6), '首次发布', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),

  ('KV-VPN-CONNECT-2', 'KA-VPN-CONNECT', 2,
   JSON_OBJECT(
     'title', 'VPN 无法连接的排查步骤',
     'summary', 'VPN 连接失败常见于客户端版本过旧、本地网络受限或账号未开通 VPN 权限。',
     'keywords', 'VPN 无法连接 拨号 超时 远程办公',
     'body', '1. 确认客户端为公司发布的最新版本。2. 切换到手机热点排除本地网络限制。3. 确认账号已开通 VPN 权限,未开通需走权限申请。4. 记录错误码后转人工。'),
   'U004', 'U006', UTC_TIMESTAMP(6), '更新客户端版本要求', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),

  ('KV-WIFI-SLOW-1', 'KA-WIFI-SLOW', 1,
   JSON_OBJECT(
     'title', '办公室 WiFi 速度慢的处理方式',
     'summary', 'WiFi 变慢通常与信道拥塞、终端过多或距离过远有关。',
     'keywords', 'WiFi 无线 网速慢 卡顿',
     'body', '1. 优先连接 5GHz 频段。2. 靠近 AP 覆盖区域。3. 关闭后台大流量应用。4. 持续变慢请转人工并提供工位号。'),
   'U005', 'U006', UTC_TIMESTAMP(6), '首次发布', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),

  ('KV-OLD-MAIL-1', 'KA-OLD-MAIL', 1,
   JSON_OBJECT('title', '旧邮箱迁移说明', 'summary', '该流程已下线。',
               'keywords', '邮箱 迁移', 'body', '已废弃的迁移步骤。'),
   'U004', 'U006', UTC_TIMESTAMP(6), '首次发布', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6));
