// IT 服务工单系统 · 后端入口
const path = require('path');
const express = require('express');
const cors = require('cors');
const { mockAuth } = require('./middleware/auth');
const errorHandler = require('./middleware/errorHandler');
const ticketRoutes = require('./routes/tickets');
const userRoutes = require('./routes/users');
const assetRoutes = require('./routes/assets');
const kbRoutes = require('./routes/kb');
const uploadRoutes = require('./routes/uploads');
const notifyRoutes = require('./routes/notify');
const userController = require('./controllers/userController');
const { startScheduler } = require('./services/scheduler');

const app = express();
const PORT = process.env.PORT || 3001;

// 全局中间件
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// 静态资源：上传的附件（无需认证，供前端 <img> 直接访问）
app.use('/uploads', express.static(path.join(__dirname, '..', 'uploads')));

// 健康检查
app.get('/api/health', (req, res) => res.json({ status: 'ok', timestamp: new Date().toISOString() }));

// 白名单：无需认证的接口（Mock 登录选项）
app.get('/api/v1/users/login-options', userController.loginOptions);

// Mock 认证（以下路由都需要 X-User-Id）
app.use(mockAuth);

// 路由
app.use('/api/v1/tickets', ticketRoutes);
app.use('/api/v1/users', userRoutes);
app.use('/api/v1/assets', assetRoutes);
app.use('/api/v1/uploads', uploadRoutes);
app.use('/api/v1/notify', notifyRoutes);
app.use('/api/kb', kbRoutes);

// 错误处理
app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`✅ IT工单系统后端已启动: http://localhost:${PORT}`);
  console.log(`📋 API Base: /api/v1`);
  // 启动 SLA 定时任务（超时取消 / 自动验收 / 超时预警）
  startScheduler();
});

module.exports = app;
