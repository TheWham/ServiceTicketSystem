-- Demo-only reviewed knowledge, fresh database seed. No destructive reset.
USE it_ticket_system;
SET time_zone = '+00:00';
INSERT INTO knowledge_article
  (article_id, status, current_version_id, category_id, risk_level, version, created_at, updated_at)
VALUES
  ('KA-PRINTER-OFFLINE', 'PUBLISHED', 'KV-PRINTER-OFFLINE-1', 'C_HW_PR',  'NORMAL', 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('KA-VPN-CONNECT',     'PUBLISHED', 'KV-VPN-CONNECT-2',     'C_NET', 'NORMAL', 2, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  ('KA-WIFI-SLOW',       'PUBLISHED', 'KV-WIFI-SLOW-1',       'C_NET', 'NORMAL', 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),
  -- 已下线文章:用于验证 AI 与搜索都不得返回它(AC-27、RD-006)
  ('KA-OLD-MAIL',        'OFFLINE',   'KV-OLD-MAIL-1',        'C_ACC', 'NORMAL', 1, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6));

INSERT INTO knowledge_version
  (version_id, article_id, version_no, content_json, author_id, reviewer_id, published_at, change_note, created_at, updated_at)
VALUES
  ('KV-PRINTER-OFFLINE-1', 'KA-PRINTER-OFFLINE', 1,
   JSON_OBJECT(
     'title', '打印机显示离线的排查步骤',
     'summary', '打印机离线多数由网络断开、驱动异常或队列卡死引起,按顺序排查可自助恢复。',
     'keywords', '打印机 离线 无法打印 队列 驱动',
     'body', '1. 确认打印机电源与网线/无线指示灯正常。2. 在系统设置中删除卡住的打印队列任务。3. 重启打印后台处理程序服务。4. 若仍离线,重新安装厂商驱动。5. 以上无效请转人工或提交工单,注明打印机资产编号。'),
   'U_ENG01', 'U_KBA01', UTC_TIMESTAMP(6), '首次发布', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),

  ('KV-VPN-CONNECT-1', 'KA-VPN-CONNECT', 1,
   JSON_OBJECT('title', 'VPN 无法连接(旧版)', 'summary', '旧版步骤,已被 v2 取代。',
               'keywords', 'VPN 连接', 'body', '旧版内容。'),
   'U_ENG01', 'U_KBA01', UTC_TIMESTAMP(6), '首次发布', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),

  ('KV-VPN-CONNECT-2', 'KA-VPN-CONNECT', 2,
   JSON_OBJECT(
     'title', 'VPN 无法连接的排查步骤',
     'summary', 'VPN 连接失败常见于客户端版本过旧、本地网络受限或账号未开通 VPN 权限。',
     'keywords', 'VPN 无法连接 拨号 超时 远程办公',
     'body', '1. 确认客户端为公司发布的最新版本。2. 切换到手机热点排除本地网络限制。3. 确认账号已开通 VPN 权限,未开通需走权限申请。4. 记录错误码后转人工。'),
   'U_ENG01', 'U_KBA01', UTC_TIMESTAMP(6), '更新客户端版本要求', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),

  ('KV-WIFI-SLOW-1', 'KA-WIFI-SLOW', 1,
   JSON_OBJECT(
     'title', '办公室 WiFi 速度慢的处理方式',
     'summary', 'WiFi 变慢通常与信道拥塞、终端过多或距离过远有关。',
     'keywords', 'WiFi 无线 网速慢 卡顿',
     'body', '1. 优先连接 5GHz 频段。2. 靠近 AP 覆盖区域。3. 关闭后台大流量应用。4. 持续变慢请转人工并提供工位号。'),
   'U_ENG01', 'U_KBA01', UTC_TIMESTAMP(6), '首次发布', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6)),

  ('KV-OLD-MAIL-1', 'KA-OLD-MAIL', 1,
   JSON_OBJECT('title', '旧邮箱迁移说明', 'summary', '该流程已下线。',
               'keywords', '邮箱 迁移', 'body', '已废弃的迁移步骤。'),
   'U_ENG01', 'U_KBA01', UTC_TIMESTAMP(6), '首次发布', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6));
