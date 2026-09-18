// SQLite 数据库层 —— 提供 MySQL 风格异步 API 兼容层
const path = require('path');
const fs = require('fs');
const Database = require('better-sqlite3');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, '..', 'db', 'it_ticket.db');

// 确保目录存在
const dir = path.dirname(DB_PATH);
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');
// 并发写入时不要直接抛 SQLITE_BUSY，等待锁释放
db.pragma('busy_timeout = 5000');
// WAL 下 NORMAL 已足以保证进程崩溃不丢数据，且写入更快
db.pragma('synchronous = NORMAL');

/**
 * SQL 方言转换：MySQL → SQLite
 */
function translate(sql) {
  return sql
    .replace(/DATE_SUB\(\s*NOW\(\)\s*,\s*INTERVAL\s+(\d+)\s+MINUTE\s*\)/gi,
             "datetime('now','localtime','-$1 minute')")
    .replace(/NOW\(\)/gi, "datetime('now','localtime')");
}

function isSelect(sql) {
  return /^\s*(SELECT|WITH|PRAGMA)/i.test(sql);
}

// 将 Date 对象转换为 SQLite 可绑定的本地时间字符串
function toLocalDateTime(d) {
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ` +
         `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

function sanitize(params) {
  return params.map(v => {
    if (v instanceof Date) return toLocalDateTime(v);
    if (typeof v === 'boolean') return v ? 1 : 0;
    if (v === undefined) return null;
    return v;
  });
}

/**
 * 执行查询（兼容 mysql2 的 [rows, fields] 返回格式）
 */
async function query(sql, params = []) {
  const text = translate(sql);
  const stmt = db.prepare(text);
  const args = sanitize(params);
  if (isSelect(text)) {
    const rows = stmt.all(...args);
    return [rows, []];
  }
  const info = stmt.run(...args);
  return [{ affectedRows: info.changes, insertId: info.lastInsertRowid }, []];
}

/**
 * 模拟连接对象（支持事务）
 */
function createConnection() {
  return {
    query,
    async beginTransaction() { db.exec('BEGIN'); },
    async commit() { db.exec('COMMIT'); },
    async rollback() { try { db.exec('ROLLBACK'); } catch (e) { /* 无活动事务 */ } },
    release() { /* sqlite 无需释放 */ }
  };
}

const pool = {
  query,
  async getConnection() { return createConnection(); },
  // 关闭前把 WAL 合并回主库文件，避免数据只留在 -wal 里
  async end() {
    try { db.pragma('wal_checkpoint(TRUNCATE)'); } catch (e) { /* ignore */ }
    db.close();
  }
};

module.exports = pool;
module.exports.raw = db;
