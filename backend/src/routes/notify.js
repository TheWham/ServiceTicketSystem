const { Router } = require('express');
const notifyController = require('../controllers/notifyController');

const router = Router();

// 通知触发（挂载路径 /api/v1/notify 由主 agent 在 index.js 配置）
router.post('/dispatch', notifyController.dispatch);

module.exports = router;
