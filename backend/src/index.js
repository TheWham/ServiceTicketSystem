// IT 服务工单系统 · 后端入口
const express = require('express');
const cors = require('cors');
const { mockAuth } = require('./middleware/auth');
const errorHandler = require('./middleware/errorHandler');
const ticketRoutes = require('./routes/tickets');
const userRoutes = require('./routes/users');
const userController = require('./controllers/userController');
const pool = require('./db');

const app = express();
const PORT = process.env.PORT || 3001;

// 全局中间件
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// 健康检查
app.get('/api/health', (req, res) => res.json({ status: 'ok', timestamp: new Date().toISOString() }));

// 白名单：无需认证的接口（Mock 登录选项）
app.get('/api/v1/users/login-options', userController.loginOptions);

// Mock 认证（以下路由都需要 X-User-Id）
app.use(mockAuth);

// 路由
app.use('/api/v1/tickets', ticketRoutes);
app.use('/api/v1/users', userRoutes);

// 错误处理
app.use(errorHandler);

const server = app.listen(PORT, () => {
  console.log(`✅ IT工单系统后端已启动: http://localhost:${PORT}`);
  console.log(`📋 API Base: /api/v1`);
});

// 优雅关闭：退出前 checkpoint WAL，确保数据全部落盘
let shuttingDown = false;
async function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  console.log(`\n⏹  收到 ${signal}，正在关闭...`);
  server.close(async () => {
    try {
      await pool.end();
      console.log('✅ 数据库已安全关闭，数据已落盘');
    } catch (e) {
      console.error('关闭数据库失败:', e.message);
    }
    process.exit(0);
  });
  // 兜底：5 秒内未关闭则强制退出
  setTimeout(() => process.exit(0), 5000).unref();
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

module.exports = app;