// 数据库初始化脚本：建表 + 种子数据
//
// 安全策略：
//   默认（npm run db:init）   —— 只建表；仅当库为空时才写入种子数据，绝不覆盖已有工单
//   强制（npm run db:reset）  —— 清空全部数据并重新写入种子（需显式传 --force）
const path = require('path');
const fs = require('fs');
const Database = require('better-sqlite3');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, '..', 'db', 'it_ticket.db');
const dbDir = path.dirname(DB_PATH);
if (!fs.existsSync(dbDir)) fs.mkdirSync(dbDir, { recursive: true });

const force = process.argv.includes('--force') || process.argv.includes('-f');

const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('busy_timeout = 5000');

const schema = fs.readFileSync(path.join(__dirname, 'schema.sqlite.sql'), 'utf8');
const seed = fs.readFileSync(path.join(__dirname, 'seed.sqlite.sql'), 'utf8');

// ---------- 1. 建表（幂等，不会动已有数据） ----------
console.log('📦 正在建表...');
db.exec(schema);
console.log('✅ 建表完成');

// ---------- 2. 种子数据 ----------
function countRows(table) {
  try {
    return db.prepare(`SELECT COUNT(*) AS c FROM ${table}`).get().c;
  } catch (e) {
    return 0;
  }
}

const existingTickets = countRows('ticket');
const existingUsers = countRows('user');

// 种子数据全部使用 INSERT OR IGNORE / WHERE NOT EXISTS，可重复执行不会产生重复或覆盖已有数据
if (force) {
  console.log('⚠️  检测到 --force，将清空全部数据并重建...');
  db.exec('DELETE FROM ticket_flow_log; DELETE FROM notification_log; DELETE FROM ticket_draft; DELETE FROM ticket;');
  db.exec(seed);
  console.log('✅ 已重置并写入种子数据');
} else {
  db.exec(seed);
  console.log(`🌱 种子数据已同步（幂等，已有 ${existingUsers} 个用户 / ${existingTickets} 张工单不会被覆盖）`);
}

// ---------- 3. 汇总 ----------
const users = db.prepare('SELECT user_id, name, role FROM user').all();
const tickets = db.prepare('SELECT ticket_id, status FROM ticket').all();
console.log(`\n👥 用户 (${users.length}):`);
users.forEach(u => console.log(`   ${u.user_id}  ${u.name}  [${u.role}]`));
console.log(`\n🎫 工单 (${tickets.length}):`);
tickets.forEach(t => console.log(`   ${t.ticket_id}  ${t.status}`));
console.log(`\n📁 数据库文件: ${DB_PATH}`);

db.close();
