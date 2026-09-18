// IT 服务工单系统 · 后端入口
const express = require('express');
const cors = require('cors');
const { mockAuth } = require('./middleware/auth');
const errorHandler = require('./middleware/errorHandler');
const ticketRoutes = require('./routes/tickets');
const userRoutes = require('./routes/users');
const userController = require('./controllers/userController');

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

app.listen(PORT, () => {
  console.log(`✅ IT工单系统后端已启动: http://localhost:${PORT}`);
  console.log(`📋 API Base: /api/v1`);
});

module.exports = app;