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
 * 异步互斥锁
 *
 * better-sqlite3 是单连接同步驱动，db.js 又把它包装成了“连接池”供异步代码使用。
 * 两个请求的事务一旦交错（await 处让出控制权），第二个 BEGIN 就会报
 * “cannot start a transaction within a transaction” → 间歇性 500。
 * 用互斥锁保证同一时刻只有一个事务在跑。
 */
class Mutex {
  constructor() { this._tail = Promise.resolve(); }
  async lock() {
    let release;
    const gate = new Promise(res => { release = res; });
    const prev = this._tail;
    this._tail = prev.then(() => gate);
    await prev;
    return release;
  }
}

const txMutex = new Mutex();

/**
 * 模拟连接对象（支持事务）
 */
function createConnection() {
  let unlock = null;

  function releaseLock() {
    if (unlock) { const u = unlock; unlock = null; u(); }
  }

  return {
    query,
    async beginTransaction() {
      unlock = await txMutex.lock();
      try {
        // IMMEDIATE：开局就取写锁，避开延迟事务升级导致的 SQLITE_BUSY
        db.exec('BEGIN IMMEDIATE');
      } catch (e) {
        releaseLock();
        throw e;
      }
    },
    async commit() {
      try { db.exec('COMMIT'); }
      finally { releaseLock(); }
    },
    async rollback() {
      try { db.exec('ROLLBACK'); } catch (e) { /* 无活动事务 */ }
      finally { releaseLock(); }
    },
    // 兼容层：若调用方忘了提交/回滚，释放锁并回滚，避免后续请求全部卡死
    release() {
      if (unlock) {
        try { db.exec('ROLLBACK'); } catch (e) { /* ignore */ }
        releaseLock();
      }
    }
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
