const groups = {
  pool: ['ASSIGNED'],
  tasks: ['IN_PROGRESS', 'PENDING_SUPPLEMENT', 'PENDING_EXTERNAL', 'PENDING_ACCEPTANCE'],
  completed: ['COMPLETED', 'CANCELLED', 'CLOSED'],
  consultations: []
}
export function engineerView(query) {
  return typeof query === 'string' && Object.hasOwn(groups, query) ? query : 'all'
}
export function engineerStatuses(view) {
  return groups[view] || [...groups.pool, ...groups.tasks, ...groups.completed]
}
export function filterEngineerTickets(tickets, view, keyword = '') {
  const statuses = engineerStatuses(view)
  const search = keyword.trim().toLowerCase()
  return tickets.filter(ticket => statuses.includes(ticket.status) && (!search || ['ticket_id', 'title', 'creator_name'].some(field => String(ticket[field] || '').toLowerCase().includes(search))))
}
