// Ticket Controller —— 工单 CRUD + 状态操作
const pool = require('../db');
const { generateTicketId } = require('../services/idGenerator');
const { validateTransition, resolveAction, getEventType, getNotifyReceivers, STATUS } = require('../services/stateMachine');
const { sendNotification } = require('../services/notification');

// POST /api/v1/tickets —— 创建工单
async function createTicket(req, res, next) {
  const conn = await pool.getConnection();
  try {
    const { category, title, description, priority = '中', attachment_urls, expected_finish_time, client_token, asset_id } = req.body;
    const creator = req.currentUser;

    // 参数校验
    const errors = [];
    if (!['硬件','软件','网络','账号','其他'].includes(category)) errors.push('问题分类无效');
    if (!title || typeof title !== 'string' || title.trim().length < 1 || title.trim().length > 50) errors.push('标题为必填且不超过50字符');
    if (!description || description.trim().length < 10) errors.push('问题描述至少10个字符');
    if (description && description.trim().length > 500) errors.push('问题描述不能超过500字符');
    if (!['高','中','低'].includes(priority)) errors.push('优先级无效');
    if (attachment_urls && (!Array.isArray(attachment_urls) || attachment_urls.length > 3)) errors.push('截图附件最多3张');
    if (expected_finish_time && new Date(expected_finish_time) < new Date()) errors.push('期望完成时间不能早于当前时间');
    if (asset_id && !/^IT-[A-Z]{2,4}-\d{8}$/.test(asset_id)) {
      errors.push('资产编号格式无效');
    } else if (asset_id) {
      const [assets] = await conn.query('SELECT asset_id FROM asset WHERE asset_id = ?', [asset_id]);
      if (assets.length === 0) errors.push('资产编号不存在');
    }
    if (errors.length > 0) return res.status(400).json({ code: 40001, msg: errors.join('；'), data: null });

    // 幂等检查
    if (client_token) {
      const [existing] = await conn.query('SELECT ticket_id FROM ticket WHERE client_token = ?', [client_token]);
      if (existing.length > 0) {
        return res.status(200).json({ code: 0, msg: '重复提交(幂等)', data: { ticket_id: existing[0].ticket_id } });
      }
    }

    // 生成工单号
    const ticketId = await generateTicketId();

    await conn.beginTransaction();

    // 插入工单（first_response_at 初始为 NULL，status_changed_at 记录进入当前状态的时间）
    await conn.query(
      `INSERT INTO ticket (ticket_id, title, description, category, priority, status, creator_id, asset_id,
        expected_finish_time, attachment_urls, client_token, status_changed_at)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,NOW())`,
      [ticketId, title.trim(), description.trim(), category, priority, STATUS.PENDING, creator.user_id,
       asset_id || null, expected_finish_time || null,
       attachment_urls ? JSON.stringify(attachment_urls) : null, client_token || null]
    );

    // 记录流水
    await conn.query(
      'INSERT INTO ticket_flow_log (ticket_id, to_status, operator_id, remark) VALUES (?,?,?,?)',
      [ticketId, STATUS.PENDING, creator.user_id, '提交工单']
    );

    await conn.commit();

    // 异步通知(不阻塞响应)
    sendNotification(ticketId, 'SUBMIT_SUCCESS', creator.user_id).catch(console.error);

    res.status(201).json({
      code: 0, msg: '创建成功',
      data: { ticket_id: ticketId, status: STATUS.PENDING, title: title.trim() }
    });
  } catch (err) { await conn.rollback(); next(err); }
  finally { conn.release(); }
}

// 解析 attachment_urls JSON 字段
function parseTicketRow(row) {
  if (row && row.attachment_urls && typeof row.attachment_urls === 'string') {
    try { row.attachment_urls = JSON.parse(row.attachment_urls); } catch (e) { row.attachment_urls = []; }
  }
  return row;
}

// GET /api/v1/tickets —— 工单列表(支持筛选)
async function listTickets(req, res, next) {
  try {
    const { status, category, assignee_id, creator_id, priority, page = 1, page_size = 20 } = req.query;
    const conditions = [];
    const params = [];

    if (status) { conditions.push('t.status = ?'); params.push(status); }
    if (category) { conditions.push('t.category = ?'); params.push(category); }
    if (assignee_id) { conditions.push('t.assignee_id = ?'); params.push(assignee_id); }
    if (creator_id) { conditions.push('t.creator_id = ?'); params.push(creator_id); }
    if (priority) { conditions.push('t.priority = ?'); params.push(priority); }

    const where = conditions.length > 0 ? 'WHERE ' + conditions.join(' AND ') : '';
    const offset = (parseInt(page) - 1) * parseInt(page_size);

    const [countResult] = await pool.query(`SELECT COUNT(*) as total FROM ticket t ${where}`, params);
    const [rows] = await pool.query(
      `SELECT t.*, c.name as creator_name, a.name as assignee_name
       FROM ticket t
       LEFT JOIN user c ON t.creator_id = c.user_id
       LEFT JOIN user a ON t.assignee_id = a.user_id
       ${where} ORDER BY t.created_at DESC LIMIT ? OFFSET ?`,
      [...params, parseInt(page_size), offset]
    );

    res.json({
      code: 0, msg: 'success',
      data: { list: rows.map(parseTicketRow), total: countResult[0].total, page: parseInt(page), page_size: parseInt(page_size) }
    });
  } catch (err) { next(err); }
}

// GET /api/v1/tickets/:id —— 工单详情(含流水)
async function getTicket(req, res, next) {
  try {
    const { id } = req.params;
    const [tickets] = await pool.query(
      `SELECT t.*, c.name as creator_name, a.name as assignee_name
       FROM ticket t LEFT JOIN user c ON t.creator_id = c.user_id LEFT JOIN user a ON t.assignee_id = a.user_id
       WHERE t.ticket_id = ?`, [id]
    );
    if (tickets.length === 0) return res.status(404).json({ code: 40400, msg: '工单不存在' });

    const [flows] = await pool.query(
      `SELECT f.*, u.name as operator_name FROM ticket_flow_log f
       LEFT JOIN user u ON f.operator_id = u.user_id
       WHERE f.ticket_id = ? ORDER BY f.created_at ASC`, [id]
    );

    res.json({ code: 0, msg: 'success', data: { ticket: parseTicketRow(tickets[0]), flow_logs: flows } });
  } catch (err) { next(err); }
}

// GET /api/v1/tickets/stats —— 全局各状态计数（支持按处理人过滤）
async function stats(req, res, next) {
  try {
    const { assignee_id } = req.query;
    const conditions = [];
    const params = [];
    if (assignee_id) { conditions.push('assignee_id = ?'); params.push(assignee_id); }
    const where = conditions.length > 0 ? 'WHERE ' + conditions.join(' AND ') : '';

    const [rows] = await pool.query(`SELECT status, COUNT(*) as cnt FROM ticket ${where} GROUP BY status`, params);

    const allStatuses = [STATUS.PENDING, STATUS.PROCESSING, STATUS.NEED_INFO, STATUS.EXTERNAL, STATUS.ACCEPTANCE, STATUS.DONE, STATUS.CANCELLED];
    const data = {};
    let total = 0;
    for (const s of allStatuses) data[s] = 0;
    for (const r of rows) {
      data[r.status] = r.cnt;
      total += r.cnt;
    }
    data['全部'] = total;

    res.json({ code: 0, msg: 'success', data });
  } catch (err) { next(err); }
}

// POST /api/v1/tickets/:id/assign —— 派单/改派
async function assignTicket(req, res, next) {
  const conn = await pool.getConnection();
  try {
    const { id } = req.params;
    const { assignee_id, reason } = req.body;
    const operator = req.currentUser;

    if (!assignee_id) return res.status(400).json({ code: 40001, msg: '请选择处理人' });

    // 校验处理人
    const [users] = await conn.query('SELECT * FROM user WHERE user_id = ? AND role = ? AND status = ?', [assignee_id, 'engineer', 'active']);
    if (users.length === 0) return res.status(400).json({ code: 40021, msg: '处理人无效或非在职工程师' });

    const [tickets] = await conn.query('SELECT * FROM ticket WHERE ticket_id = ?', [id]);
    if (tickets.length === 0) return res.status(404).json({ code: 40400, msg: '工单不存在' });
    const ticket = tickets[0];

    // 校验状态转移
    const validation = validateTransition(ticket.status, STATUS.PROCESSING, operator.role);
    if (!validation.valid) return res.status(409).json({ code: 40910, msg: validation.msg });

    const oldAssignee = ticket.assignee_id;
    const isReassign = oldAssignee && oldAssignee !== assignee_id;

    await conn.beginTransaction();
    await conn.query('UPDATE ticket SET assignee_id = ?, status = ?, first_response_at = COALESCE(first_response_at, NOW()), status_changed_at = NOW() WHERE ticket_id = ?',
      [assignee_id, STATUS.PROCESSING, id]);
    await conn.query('INSERT INTO ticket_flow_log (ticket_id, from_status, to_status, operator_id, remark) VALUES (?,?,?,?,?)',
      [id, ticket.status, STATUS.PROCESSING, operator.user_id, isReassign ? `改派: ${reason || '无'}` : `派单: ${reason || '无'}`]);
    await conn.commit();

    sendNotification(id, 'DISPATCH', assignee_id, '企微', ticket.priority).catch(console.error);

    res.json({ code: 0, msg: isReassign ? '改派成功' : '派单成功', data: { ticket_id: id, status: STATUS.PROCESSING, assignee_id } });
  } catch (err) { await conn.rollback(); next(err); }
  finally { conn.release(); }
}

// POST /api/v1/tickets/:id/actions —— 状态操作
async function actionTicket(req, res, next) {
  const conn = await pool.getConnection();
  try {
    const { id } = req.params;
    const { action, remark } = req.body;
    const operator = req.currentUser;

    const [tickets] = await conn.query('SELECT * FROM ticket WHERE ticket_id = ?', [id]);
    if (tickets.length === 0) return res.status(404).json({ code: 40400, msg: '工单不存在' });
    const ticket = tickets[0];

    // 特例 progress：记录进展，不改变状态（仅处理中/待补充/待外部允许）
    if (action === 'progress') {
      if (![STATUS.PROCESSING, STATUS.NEED_INFO, STATUS.EXTERNAL].includes(ticket.status)) {
        return res.status(409).json({ code: 40910, msg: `当前状态「${ticket.status}」不允许「progress」操作` });
      }
      if (!remark || remark.trim().length < 5) {
        return res.status(400).json({ code: 40001, msg: '进展说明至少5个字符' });
      }
      await conn.beginTransaction();
      await conn.query('INSERT INTO ticket_flow_log (ticket_id, from_status, to_status, operator_id, remark) VALUES (?,?,?,?,?)',
        [id, ticket.status, ticket.status, operator.user_id, remark.trim()]);
      await conn.commit();
      return res.json({ code: 0, msg: '进展已记录', data: { ticket_id: id, status: ticket.status } });
    }

    // 统一状态机校验：根据 action 解析目标状态与转移项
    const resolved = resolveAction(ticket.status, action);
    if (!resolved) {
      return res.status(409).json({ code: 40910, msg: `当前状态「${ticket.status}」不允许「${action}」操作` });
    }
    const targetStatus = resolved.to;

    // 特定操作 remark 长度校验
    if (action === 'need_info' && (!remark || remark.trim().length < 5)) return res.status(400).json({ code: 40001, msg: '补充信息说明至少5个字符' });
    if (action === 'reject' && (!remark || remark.length < 10)) return res.status(400).json({ code: 40001, msg: '驳回原因至少10个字符' });
    if (action === 'external' && (!remark || remark.length < 10)) return res.status(400).json({ code: 40001, msg: '外部依赖说明至少10个字符' });

    // 工程师完成前至少有一条进展记录
    if (action === 'done' && operator.role === 'engineer') {
      const [logs] = await conn.query("SELECT COUNT(*) as cnt FROM ticket_flow_log WHERE ticket_id = ? AND operator_id = ? AND remark != '提交工单'", [id, operator.user_id]);
      if (logs[0].cnt === 0) return res.status(400).json({ code: 40001, msg: '请至少记录一条处理进展后再提交' });
    }

    await conn.beginTransaction();

    const updateFields = { status: targetStatus, status_changed_at: new Date() };
    if (action === 'done' || action === 'accept' || action === 'cancel') {
      updateFields.solved_at = new Date();
    }
    // 取消时清除 assignee
    if (action === 'cancel') updateFields.assignee_id = null;

    const setClauses = Object.keys(updateFields).map(k => `${k} = ?`).join(', ');
    await conn.query(`UPDATE ticket SET ${setClauses} WHERE ticket_id = ?`,
      [...Object.values(updateFields), id]);

    const flowRemark = remark || targetStatus;
    await conn.query('INSERT INTO ticket_flow_log (ticket_id, from_status, to_status, operator_id, remark) VALUES (?,?,?,?,?)',
      [id, ticket.status, targetStatus, operator.user_id, flowRemark]);
    await conn.commit();

    // 通知（高优先级工单传入 priority 以启用短信兜底）
    const eventType = getEventType(ticket.status, targetStatus, action);
    const receivers = getNotifyReceivers({ ...ticket, ...updateFields }, targetStatus);
    receivers.forEach(r => sendNotification(id, eventType, r.id, '企微', ticket.priority).catch(console.error));

    res.json({ code: 0, msg: '操作成功', data: { ticket_id: id, status: targetStatus } });
  } catch (err) { await conn.rollback(); next(err); }
  finally { conn.release(); }
}

// POST /api/v1/tickets/:id/rating —— 满意度评价
async function rateTicket(req, res, next) {
  try {
    const { id } = req.params;
    const { score, comment } = req.body;
    if (!score || score < 1 || score > 5) return res.status(400).json({ code: 40001, msg: '评分须为 1-5' });
    if (comment && comment.length > 200) return res.status(400).json({ code: 40001, msg: '评语不超过200字' });

    const [tickets] = await pool.query('SELECT * FROM ticket WHERE ticket_id = ? AND status = ?', [id, STATUS.DONE]);
    if (tickets.length === 0) return res.status(400).json({ code: 40001, msg: '仅已完成的工单可评价' });

    await pool.query('UPDATE ticket SET rating_score = ?, rating_comment = ?, rated_at = NOW() WHERE ticket_id = ?',
      [score, comment || null, id]);

    res.json({ code: 0, msg: '评价成功' });
  } catch (err) { next(err); }
}

module.exports = { createTicket, listTickets, getTicket, stats, assignTicket, actionTicket, rateTicket };
