// Notify Controller —— 独立通知接口
const { sendNotification } = require('../services/notification');

// POST /api/v1/notify/dispatch —— 触发通知（供定时任务/外部系统调用）
async function dispatch(req, res, next) {
  try {
    const { ticket_id, event_type, receiver_id, priority = '中', template_params } = req.body;
    if (!ticket_id || !event_type || !receiver_id) {
      return res.status(400).json({ code: 40001, msg: 'ticket_id、event_type、receiver_id 为必填' });
    }
    const result = await sendNotification(ticket_id, event_type, receiver_id, '企微', priority);
    res.json({ code: 0, msg: 'success', data: result });
  } catch (err) { next(err); }
}

module.exports = { dispatch };
