// 工单状态机引擎 —— 定义所有合法状态转移 + 副作用
const STATUS = {
  PENDING:      '待处理',
  PROCESSING:   '处理中',
  NEED_INFO:    '待补充',
  EXTERNAL:     '待外部',
  ACCEPTANCE:   '待验收',
  DONE:         '已完成',
  CANCELLED:    '已取消'
};

// 状态转移图：from → [{ to, action, role, guard? }]
const TRANSITIONS = {
  [STATUS.PENDING]: [
    { to: STATUS.PROCESSING, action: 'assign',     role: ['supervisor'],           remark: '派单' },
    // 工程师自主领取未派单工单：与 supervisor 派单等价，只是操作者不同
    { to: STATUS.PROCESSING, action: 'claim',      role: ['engineer'],             remark: '领取工单' },
    { to: STATUS.CANCELLED,  action: 'cancel',     role: ['employee'],             remark: '撤回',  guard: 'no_flow_log' }
  ],
  [STATUS.PROCESSING]: [
    { to: STATUS.NEED_INFO,  action: 'need_info',  role: ['engineer'],             remark: '申请补充信息' },
    { to: STATUS.EXTERNAL,   action: 'external',   role: ['engineer'],             remark: '需外部支持', guard: 'has_remark_10' },
    { to: STATUS.ACCEPTANCE, action: 'done',       role: ['engineer'],             remark: '提交方案', guard: 'has_flow_log' }
  ],
  [STATUS.NEED_INFO]: [
    { to: STATUS.PROCESSING, action: 'supply_info',role: ['employee'],             remark: '补充信息' },
    { to: STATUS.CANCELLED,  action: 'timeout',    role: ['system'],              remark: '超时未补充' }
  ],
  [STATUS.EXTERNAL]: [
    { to: STATUS.PROCESSING, action: 'external_resolved', role: ['engineer','supervisor'], remark: '外部解除' }
  ],
  [STATUS.ACCEPTANCE]: [
    { to: STATUS.DONE,       action: 'accept',     role: ['employee'],             remark: '验收通过' },
    { to: STATUS.PROCESSING, action: 'reject',     role: ['employee'],             remark: '驳回',   guard: 'reject_reason_10' },
    { to: STATUS.DONE,       action: 'auto_accept',role: ['system'],              remark: '超时自动通过(3工作日)' }
  ]
};

const TERMINAL_STATUSES = [STATUS.DONE, STATUS.CANCELLED];

// 校验状态转移是否合法
// action 可选：指定后精确匹配该动作，否则在所有通向目标状态的转移中选一个当前角色有权执行的
function validateTransition(fromStatus, toStatus, userRole, action) {
  const allowed = TRANSITIONS[fromStatus];
  if (!allowed) {
    return { valid: false, msg: `当前状态「${fromStatus}」已是终态或不可操作` };
  }

  const candidates = allowed.filter(t => t.to === toStatus && (!action || t.action === action));

  if (candidates.length === 0) {
    const allowedTo = allowed.map(t => t.to).join('、');
    return { valid: false, msg: `不允许从「${fromStatus}」转到「${toStatus}」，允许的目标状态：${allowedTo}` };
  }

  // 优先选一个当前角色有权执行的转移（同一目标状态可能对应多个动作，如 assign / claim）
  const match = candidates.find(t => t.role.includes(userRole) || t.role.includes('system'));

  if (!match) {
    const requiredRoles = [...new Set(candidates.flatMap(t => t.role))].join(' 或 ');
    return { valid: false, msg: `角色「${userRole}」无权执行此操作（需要 ${requiredRoles}）` };
  }

  return { valid: true, transition: match };
}

// 判断通知事件类型
function getEventType(fromStatus, toStatus, action) {
  const map = {
    'assign':            'DISPATCH',
    'claim':             'DISPATCH',
    'cancel':            'CANCEL',
    'need_info':         'PENDING_SUPPLEMENT',
    'external':          'PENDING_EXTERNAL',
    'done':              'PENDING_ACCEPTANCE',
    'accept':            'ACCEPT_APPROVED',
    'auto_accept':       'ACCEPT_APPROVED',
    'reject':            'ACCEPT_REJECTED',
    'supply_info':       'INFO_SUPPLIED',
    'timeout':           'TIMEOUT_CANCEL',
    'external_resolved': 'EXTERNAL_RESOLVED'
  };
  return map[action] || 'STATUS_CHANGED';
}

// 获取通知接收人
function getNotifyReceivers(ticket, toStatus) {
  const receivers = [];
  if (toStatus === STATUS.PROCESSING && ticket.assignee_id) {
    receivers.push({ id: ticket.assignee_id, role: 'engineer' });
  }
  if (toStatus === STATUS.NEED_INFO || toStatus === STATUS.ACCEPTANCE) {
    receivers.push({ id: ticket.creator_id, role: 'employee' });
  }
  if (toStatus === STATUS.EXTERNAL) {
    receivers.push({ id: ticket.creator_id, role: 'employee' });
    if (ticket.assignee_id) receivers.push({ id: ticket.assignee_id, role: 'engineer' });
  }
  if (toStatus === STATUS.DONE || toStatus === STATUS.CANCELLED) {
    receivers.push({ id: ticket.creator_id, role: 'employee' });
    if (ticket.assignee_id) receivers.push({ id: ticket.assignee_id, role: 'engineer' });
  }
  return receivers;
}

module.exports = {
  STATUS,
  TRANSITIONS,
  TERMINAL_STATUSES,
  validateTransition,
  getEventType,
  getNotifyReceivers
};