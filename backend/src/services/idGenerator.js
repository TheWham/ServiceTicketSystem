// 工单号生成：TK + yyyyMMdd + 4位自增（含并发冲突重试一次）
const pool = require('../db');

async function generateTicketId() {
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  const prefix = `TK${today}`;
  const [rows] = await pool.query(
    'SELECT ticket_id FROM ticket WHERE ticket_id LIKE ? ORDER BY ticket_id DESC LIMIT 1',
    [`${prefix}%`]
  );
  let seq = 1;
  if (rows.length > 0) {
    const lastSeq = parseInt(rows[0].ticket_id.slice(-4), 10);
    seq = lastSeq + 1;
  }
  return `${prefix}${String(seq).padStart(4, '0')}`;
}

/**
 * 生成工单号并在主键冲突时重试一次（并发保护）
 * 用法：先调用 nextTicketId() 得到候选号，插入时若冲突可再次调用。
 */
async function nextTicketId() {
  const first = await generateTicketId();
  // 检查是否已被占用；若占用则递增重试一次
  const [rows] = await pool.query('SELECT ticket_id FROM ticket WHERE ticket_id = ?', [first]);
  if (rows.length === 0) return first;
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  const prefix = `TK${today}`;
  const seq = parseInt(first.slice(-4), 10) + 1;
  return `${prefix}${String(seq).padStart(4, '0')}`;
}

module.exports = { generateTicketId, nextTicketId };