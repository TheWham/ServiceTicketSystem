const { Router } = require('express');
const tc = require('../controllers/ticketController');
const { requireRole } = require('../middleware/auth');

const router = Router();

// 工单 CRUD
router.post('/',           tc.createTicket);              // 创建工单
router.get('/',            tc.listTickets);               // 工单列表
router.get('/:id',         tc.getTicket);                 // 工单详情

// 状态操作
router.post('/:id/assign', requireRole('supervisor'), tc.assignTicket);  // 派单(仅主管)
router.post('/:id/actions', tc.actionTicket);                             // 通用状态操作
router.post('/:id/rating', tc.rateTicket);                                // 评价

module.exports = router;