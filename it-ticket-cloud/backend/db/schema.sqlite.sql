-- ============================================================
-- IT 服务工单系统 · SQLite Schema (P0 MVP)
-- 版本: v1.0 | 2026-09-18
-- ============================================================

-- ----------------------------
-- 1. 用户表 (员工/工程师/主管)
-- ----------------------------
CREATE TABLE IF NOT EXISTS user (
  user_id     TEXT PRIMARY KEY,                                    -- 用户ID，如 U001
  name        TEXT NOT NULL,                                       -- 姓名
  role        TEXT NOT NULL CHECK (role IN ('employee','engineer','supervisor')),
  department  TEXT,
  phone       TEXT,
  wechat_id   TEXT,
  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
  created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_user_role ON user(role);
CREATE INDEX IF NOT EXISTS idx_user_dept ON user(department);

-- ----------------------------
-- 2. 工单表 (核心实体)
-- ----------------------------
CREATE TABLE IF NOT EXISTS ticket (
  ticket_id            TEXT PRIMARY KEY,                           -- TK+yyyyMMdd+4位自增
  title                TEXT NOT NULL,                              -- 1-50字符
  description          TEXT NOT NULL,                              -- 10-500字符
  category             TEXT NOT NULL CHECK (category IN ('硬件','软件','网络','账号','其他')),
  sub_category         TEXT,
  priority             TEXT NOT NULL DEFAULT '中' CHECK (priority IN ('高','中','低')),
  status               TEXT NOT NULL DEFAULT '待处理'
                       CHECK (status IN ('待处理','处理中','待补充','待外部','待验收','已完成','已取消')),
  creator_id           TEXT NOT NULL,
  assignee_id          TEXT,
  asset_id             TEXT,
  expected_finish_time TEXT,
  attachment_urls      TEXT,                                       -- JSON 数组字符串
  client_token         TEXT UNIQUE,
  first_response_at    TEXT,
  solved_at            TEXT,
  pause_minutes        INTEGER DEFAULT 0,
  rating_score         INTEGER,
  rating_comment       TEXT,
  rated_at             TEXT,
  created_at           TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at           TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_ticket_status   ON ticket(status);
CREATE INDEX IF NOT EXISTS idx_ticket_creator  ON ticket(creator_id);
CREATE INDEX IF NOT EXISTS idx_ticket_assignee ON ticket(assignee_id);
CREATE INDEX IF NOT EXISTS idx_ticket_category ON ticket(category);
CREATE INDEX IF NOT EXISTS idx_ticket_priority ON ticket(priority);
CREATE INDEX IF NOT EXISTS idx_ticket_created  ON ticket(created_at);

-- updated_at 自动更新触发器
CREATE TRIGGER IF NOT EXISTS trg_ticket_updated_at
AFTER UPDATE ON ticket
FOR EACH ROW
BEGIN
  UPDATE ticket SET updated_at = datetime('now','localtime') WHERE ticket_id = NEW.ticket_id;
END;

-- ----------------------------
-- 3. 状态流转日志表
-- ----------------------------
CREATE TABLE IF NOT EXISTS ticket_flow_log (
  log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id   TEXT NOT NULL,
  from_status TEXT,
  to_status   TEXT NOT NULL,
  operator_id TEXT NOT NULL,
  remark      TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_flow_ticket   ON ticket_flow_log(ticket_id);
CREATE INDEX IF NOT EXISTS idx_flow_operator ON ticket_flow_log(operator_id);
CREATE INDEX IF NOT EXISTS idx_flow_created  ON ticket_flow_log(created_at);

-- ----------------------------
-- 4. 通知记录表 (幂等控制)
-- ----------------------------
CREATE TABLE IF NOT EXISTS notification_log (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id       TEXT NOT NULL,
  event_type      TEXT NOT NULL,
  receiver_id     TEXT NOT NULL,
  channel         TEXT NOT NULL DEFAULT '企微' CHECK (channel IN ('企微','短信','站内')),
  is_fallback     INTEGER DEFAULT 0,
  delivery_status TEXT DEFAULT 'PENDING' CHECK (delivery_status IN ('SUCCESS','FAILED','PENDING')),
  created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_notify_ticket_event ON notification_log(ticket_id, event_type);
CREATE INDEX IF NOT EXISTS idx_notify_receiver     ON notification_log(receiver_id);

-- ----------------------------
-- 5. 草稿表
-- ----------------------------
CREATE TABLE IF NOT EXISTS ticket_draft (
  draft_id             INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id              TEXT NOT NULL UNIQUE,
  title                TEXT,
  category             TEXT,
  sub_category         TEXT,
  priority             TEXT DEFAULT '中',
  description          TEXT,
  attachment_urls      TEXT,
  asset_id             TEXT,
  expected_finish_time TEXT,
  updated_at           TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
