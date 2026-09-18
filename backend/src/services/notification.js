// 通知服务 —— 模拟企微推送 + 高优先级短信兜底
const pool = require('../db');

// 企微通道失败率：0 = 永不失败；测试可改为 0~1 以触发短信兜底
const WECHAT_FAIL_RATE = 0;

// 企微通道（模拟实现）
function wechatChannel(ticketId, eventType, receiverId) {
  console.log(`[企微] 向 ${receiverId} 推送：工单 ${ticketId} 事件 ${eventType}`);
  if (Math.random() < WECHAT_FAIL_RATE) {
    return { success: false, reason: '模拟企微发送失败' };
  }
  return { success: true };
}

// 短信通道（模拟兜底）
function smsChannel(ticketId, eventType, receiverId) {
  console.log(`[短信] 向 ${receiverId} 发送：工单 ${ticketId} 事件 ${eventType}`);
  return { success: true };
}

/**
 * 发送通知
 * @param {string} ticketId   工单号
 * @param {string} eventType  事件类型（如 DISPATCH、TIMEOUT_ALERT）
 * @param {string} receiverId 接收人 ID
 * @param {string} channel    首选通道，默认 '企微'
 * @param {string} priority   优先级，默认 '中'；仅 '高' 在企微失败时触发短信兜底
 */
async function sendNotification(ticketId, eventType, receiverId, channel = '企微', priority = '中') {
  const dedupKey = `${ticketId}:${eventType}:${receiverId}`;

  // 幂等检查：同一工单 + 同一事件 + 同一接收人 1 分钟内不重复
  const [recent] = await pool.query(
    'SELECT id FROM notification_log WHERE ticket_id = ? AND event_type = ? AND receiver_id = ? AND created_at > DATE_SUB(NOW(), INTERVAL 1 MINUTE)',
    [ticketId, eventType, receiverId]
  );
  if (recent.length > 0) {
    console.log(`[通知] 幂等跳过: ${dedupKey}`);
    return {
      sent: false,
      reason: 'dedup',
      ticket_id: ticketId,
      channel_used: channel,
      is_fallback: false,
      delivery_status: 'SUCCESS'
    };
  }

  let channelUsed = channel;
  let isFallback = false;
  let deliveryStatus = 'SUCCESS';

  // 尝试企微通道
  let wechatResult;
  try {
    wechatResult = wechatChannel(ticketId, eventType, receiverId);
  } catch (e) {
    wechatResult = { success: false, reason: e.message };
  }

  if (!wechatResult.success) {
    if (priority === '高') {
      // 高优先级：短信兜底
      let smsResult;
      try {
        smsResult = smsChannel(ticketId, eventType, receiverId);
      } catch (e) {
        smsResult = { success: false, reason: e.message };
      }
      channelUsed = '短信';
      isFallback = true;
      deliveryStatus = smsResult.success ? 'SUCCESS' : 'FAILED';
    } else {
      deliveryStatus = 'FAILED';
    }
  }

  await pool.query(
    'INSERT INTO notification_log (ticket_id, event_type, receiver_id, channel, is_fallback, delivery_status) VALUES (?,?,?,?,?,?)',
    [ticketId, eventType, receiverId, channelUsed, isFallback ? 1 : 0, deliveryStatus]
  );

  console.log(`[通知] 已发送: ${dedupKey} → ${receiverId} (${channelUsed}${isFallback ? ', 短信兜底' : ''})`);
  return {
    ticket_id: ticketId,
    channel_used: channelUsed,
    is_fallback: isFallback,
    delivery_status: deliveryStatus
  };
}

module.exports = { sendNotification, wechatChannel, smsChannel };
