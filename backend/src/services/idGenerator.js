// 工单号生成：TK + yyyyMMdd + 4位自增
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

module.exports = { generateTicketId };