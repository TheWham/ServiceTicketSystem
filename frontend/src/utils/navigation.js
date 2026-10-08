export function roleHome(role) {
  return { EMPLOYEE: '/employee', ENGINEER: '/engineer', PLATFORM_ADMIN: '/supervisor', KNOWLEDGE_ADMIN: '/knowledge-admin', KB_ADMIN: '/knowledge-admin' }[String(role).toUpperCase()] || '/login'
}
export function roleLabel(role) {
  return { EMPLOYEE: '员工', ENGINEER: '工程师', PLATFORM_ADMIN: '平台管理员', KNOWLEDGE_ADMIN: '知识库管理员', KB_ADMIN: '知识库管理员' }[String(role).toUpperCase()] || '工作空间'
}
const item = (id, label, icon, path, query = {}) => ({ id, label, icon, to: { path, query } })
export function navigationFor(role) {
  switch (String(role).toUpperCase()) {
    case 'EMPLOYEE': return [item('consultation', '智能客服', 'ChatDotRound', '/consultation'), item('create', '提交工单', 'CirclePlus', '/employee', { tab: 'create' }), item('list', '我的工单', 'Tickets', '/employee', { tab: 'list' })]
    case 'ENGINEER': return [item('all', '工作概览', 'DataBoard', '/engineer'), item('pool', '待接工单', 'Download', '/engineer', { view: 'pool' }), item('tasks', '我的任务', 'Tools', '/engineer', { view: 'tasks' }), item('completed', '已结束工单', 'CircleCheck', '/engineer', { view: 'completed' }), item('consultations', '人工咨询', 'Service', '/engineer', { view: 'consultations' })]
    case 'PLATFORM_ADMIN': return [item('supervisor', '工单管理', 'DataBoard', '/supervisor'), item('accounts', '账号管理', 'User', '/accounts')]
    case 'KNOWLEDGE_ADMIN': return [item('ingest', '文档导入', 'Upload', '/knowledge-admin', { tab: 'ingest' }), item('lifecycle', '知识管理', 'Collection', '/knowledge-admin', { tab: 'lifecycle' })]
    case 'KB_ADMIN': return [...navigationFor('KNOWLEDGE_ADMIN'), item('supervisor', '工单管理', 'DataBoard', '/supervisor'), item('accounts', '账号管理', 'User', '/accounts')]
    default: return []
  }
}
export function activeNavigation(role, route) {
  const query = route.query || {}
  if (route.path === '/employee') return query.tab === 'list' || (!query.tab && query.ticket) ? 'list' : 'create'
  if (route.path === '/engineer') return ['pool', 'tasks', 'completed', 'consultations'].includes(query.view) ? query.view : 'all'
  if (route.path === '/knowledge-admin') return query.tab === 'lifecycle' ? 'lifecycle' : 'ingest'
  return navigationFor(role).find(link => link.to.path === route.path)?.id || ''
}
