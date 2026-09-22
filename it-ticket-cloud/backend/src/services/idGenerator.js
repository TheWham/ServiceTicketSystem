// 工单号生成：TK + yyyyMMdd + 4位自增
// 注意：日期必须用本地时区，不能用 toISOString()（UTC）——
// 否则在 UTC+8 的 00:00-08:00 会算出前一天的日期，与 created_at 不一致
const pool = require('../db');

function localDateStr() {
  const d = new Date();
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`;
}

async function generateTicketId() {
  const prefix = `TK${localDateStr()}`;
  const [rows] = await pool.query(
    'SELECT ticket_id FROM ticket WHERE ticket_id LIKE ? ORDER BY ticket_id DESC LIMIT 1',
    [`${prefix}%`]
  );
  let seq = 1;
  if (rows.length > 0) {
    const lastSeq = parseInt(rows[0].ticket_id.slice(-4), 10);
    if (!Number.isNaN(lastSeq)) seq = lastSeq + 1;
  }
  return `${prefix}${String(seq).padStart(4, '0')}`;
}

module.exports = { generateTicketId, localDateStr };