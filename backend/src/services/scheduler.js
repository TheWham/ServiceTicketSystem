// SLA 定时任务 —— 定期扫描超时工单，自动状态转移 + 预警通知
const pool = require('../db');
const { STATUS, validateTransition } = require('./stateMachine');
const { sendNotification } = require('./notification');

// ===== 阈值常量（分钟/工作日，便于测试调短）=====
const TIMEOUT_NEED_INFO_MINUTES = 24 * 60; // 待补充超过该时长自动取消
const AUTO_ACCEPT_WORKDAYS     = 3;        // 待验收超过该工作日数自动验收
const ALERT_MINUTES            = 48 * 60;  // 其它中间态超过该时长向主管预警
const SCAN_INTERVAL_MS         = 60 * 1000; // 扫描周期：60 秒

// 距今 N 分钟前的时间点（Date，db.js 会格式化为本地时间字符串用于比较）
function minutesAgo(minutes) {
  return new Date(Date.now() - minutes * 60 * 1000);
}

// 距今 N 个工作日前的时间点（跳过周末，近似计算）
function workdaysAgo(workdays) {
  let d = new Date();
  let count = 0;
  while (count < workdays) {
    d = new Date(d.getTime() - 24 * 60 * 60 * 1000);
    const day = d.getDay();
    if (day !== 0 && day !== 6) count++;
  }
  return d;
}

// 查询处于指定状态且超过阈值时间的工单
async function findStaleTickets(statuses, cutoff) {
  const placeholders = statuses.map(() => '?').join(',');
  const [rows] = await pool.query(
    `SELECT * FROM ticket WHERE status IN (${placeholders}) AND COALESCE(status_changed_at, created_at) <= ?`,
    [...statuses, cutoff]
  );
  return rows;
}

// 1. 「待补充」超时 → 自动取消，通知 creator
async function handleTimeoutNeedInfo() {
  const cutoff = minutesAgo(TIMEOUT_NEED_INFO_MINUTES);
  const tickets = await findStaleTickets([STATUS.NEED_INFO], cutoff);
  for (const ticket of tickets) {
    const validation = validateTransition(ticket.status, STATUS.CANCELLED, 'system');
    if (!validation.valid) continue;

    const conn = await pool.getConnection();
    try {
      await conn.beginTransaction();
      await conn.query('UPDATE ticket SET status = ?, status_changed_at = NOW(), assignee_id = NULL WHERE ticket_id = ?',
        [STATUS.CANCELLED, ticket.ticket_id]);
      await conn.query('INSERT INTO ticket_flow_log (ticket_id, from_status, to_status, operator_id, remark) VALUES (?,?,?,?,?)',
        [ticket.ticket_id, ticket.status, STATUS.CANCELLED, 'SYSTEM', '超时未补充自动取消']);
      await conn.commit();
    } catch (e) { await conn.rollback(); throw e; }
    finally { conn.release(); }

    sendNotification(ticket.ticket_id, 'TIMEOUT_CANCEL', ticket.creator_id).catch(console.error);
    console.log(`[SLA] 工单 ${ticket.ticket_id} 超时未补充，已自动取消`);
  }
}

// 2. 「待验收」超时 → 自动验收（已完成）
async function handleAutoAccept() {
  const cutoff = workdaysAgo(AUTO_ACCEPT_WORKDAYS);
  const tickets = await findStaleTickets([STATUS.ACCEPTANCE], cutoff);
  for (const ticket of tickets) {
    const validation = validateTransition(ticket.status, STATUS.DONE, 'system');
    if (!validation.valid) continue;

    const conn = await pool.getConnection();
    try {
      await conn.beginTransaction();
      await conn.query('UPDATE ticket SET status = ?, status_changed_at = NOW(), solved_at = NOW() WHERE ticket_id = ?',
        [STATUS.DONE, ticket.ticket_id]);
      await conn.query('INSERT INTO ticket_flow_log (ticket_id, from_status, to_status, operator_id, remark) VALUES (?,?,?,?,?)',
        [ticket.ticket_id, ticket.status, STATUS.DONE, 'SYSTEM', '超时自动验收']);
      await conn.commit();
    } catch (e) { await conn.rollback(); throw e; }
    finally { conn.release(); }

    console.log(`[SLA] 工单 ${ticket.ticket_id} 超时自动验收`);
  }
}

// 3. 其它中间态（待处理/处理中/待外部）超时 → 向主管预警
async function handleTimeoutAlert() {
  const cutoff = minutesAgo(ALERT_MINUTES);
  const tickets = await findStaleTickets([STATUS.PENDING, STATUS.PROCESSING, STATUS.EXTERNAL], cutoff);

  const [supervisors] = await pool.query(
    "SELECT user_id FROM user WHERE role = 'supervisor' AND status = 'active'"
  );
  if (supervisors.length === 0) return;

  for (const ticket of tickets) {
    for (const sup of supervisors) {
      sendNotification(ticket.ticket_id, 'TIMEOUT_ALERT', sup.user_id, '企微', ticket.priority).catch(console.error);
    }
    console.log(`[SLA] 工单 ${ticket.ticket_id} 超时预警已通知 ${supervisors.length} 位主管`);
  }
}

// 单次扫描
async function scan() {
  await handleTimeoutNeedInfo();
  await handleAutoAccept();
  await handleTimeoutAlert();
}

// 启动定时任务（index.js 会调用）
function startScheduler() {
  setInterval(async () => {
    try {
      await scan();
    } catch (err) {
      console.error('[SLA] 扫描失败:', err);
    }
  }, SCAN_INTERVAL_MS);
  console.log(`[SLA] 定时任务已启动（每 ${SCAN_INTERVAL_MS / 1000} 秒扫描一次）`);
}

module.exports = { startScheduler };
