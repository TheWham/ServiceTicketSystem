// 数据库初始化脚本：建表 + 种子数据
const path = require('path');
const fs = require('fs');
const Database = require('better-sqlite3');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, '..', 'db', 'it_ticket.db');
const dbDir = path.dirname(DB_PATH);
if (!fs.existsSync(dbDir)) fs.mkdirSync(dbDir, { recursive: true });

const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');

const schema = fs.readFileSync(path.join(__dirname, 'schema.sqlite.sql'), 'utf8');
const seed = fs.readFileSync(path.join(__dirname, 'seed.sqlite.sql'), 'utf8');

console.log('📦 正在重建表结构...');
// 先删除旧表确保 schema 变更生效：CREATE TABLE IF NOT EXISTS 不会为已存在的表新增列
db.exec(`
  DROP TABLE IF EXISTS notification_log;
  DROP TABLE IF EXISTS ticket_flow_log;
  DROP TABLE IF EXISTS ticket_draft;
  DROP TABLE IF EXISTS asset;
  DROP TABLE IF EXISTS ticket;
  DROP TABLE IF EXISTS user;
`);
db.exec(schema);
console.log('✅ 建表完成');

console.log('🌱 正在写入种子数据...');
db.exec(seed);
console.log('✅ 种子数据写入完成');

const users = db.prepare('SELECT user_id, name, role FROM user').all();
const tickets = db.prepare('SELECT ticket_id, status FROM ticket').all();
const assets = db.prepare('SELECT COUNT(*) AS c FROM asset').get();
console.log(`\n👥 用户 (${users.length}):`);
users.forEach(u => console.log(`   ${u.user_id}  ${u.name}  [${u.role}]`));
console.log(`\n💻 资产 (${assets.c} 台)`);
console.log(`\n🎫 示例工单 (${tickets.length}):`);
tickets.forEach(t => console.log(`   ${t.ticket_id}  ${t.status}`));
console.log(`\n📁 数据库文件: ${DB_PATH}`);

db.close();
