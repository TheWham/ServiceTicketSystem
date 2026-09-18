// 通知服务（P0：模拟企微推送 + 短信兜底）
const pool = require('../db');

// 通知幂等：同一工单 + 同一事件 1 分钟内不重复
async function sendNotification(ticketId, eventType, receiverId, channel = '企微') {
  const dedupKey = `${ticketId}:${eventType}`;

  // 检查幂等
  const [recent] = await pool.query(
    'SELECT id FROM notification_log WHERE ticket_id = ? AND event_type = ? AND created_at > DATE_SUB(NOW(), INTERVAL 1 MINUTE)',
    [ticketId, eventType]
  );
  if (recent.length > 0) {
    console.log(`[通知] 幂等跳过: ${dedupKey}`);
    return { sent: false, reason: 'dedup' };
  }

  // 模拟发送
  const deliveryStatus = 'SUCCESS';
  const isFallback = false;

  await pool.query(
    'INSERT INTO notification_log (ticket_id, event_type, receiver_id, channel, is_fallback, delivery_status) VALUES (?,?,?,?,?,?)',
    [ticketId, eventType, receiverId, channel, isFallback ? 1 : 0, deliveryStatus]
  );

  console.log(`[通知] 已发送: ${dedupKey} → ${receiverId} (${channel})`);
  return {
    ticket_id: ticketId,
    channel_used: channel,
    is_fallback: isFallback,
    delivery_status: deliveryStatus
  };
}

module.exports = { sendNotification };