export function ticketTypeLabel(ticket) {
  return ticket?.category_snapshot || ticket?.category_name || ticket?.category_id || '未记录'
}

export function ticketNatureLabel(nature) {
  return { INCIDENT: '故障报修', SERVICE_REQUEST: '服务申请' }[nature] || nature || '未记录'
}

export function canWithdrawTicket(ticket, userId) {
  return !!userId && ticket?.creator_id === userId
    && ['NEW', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_SUPPLEMENT', 'PENDING_EXTERNAL', 'PENDING_ACCEPTANCE'].includes(ticket.status)
}

export function ticketToForm(ticket) {
  return Object.fromEntries(['nature', 'category_id', 'title', 'description', 'impact_description',
    'urgency_description', 'location', 'contact', 'asset_id'].map(key => [key, ticket[key] || '']))
}

export function editableTicketPayload(form, attachments) {
  const content = Object.fromEntries(['title', 'description', 'impact_description', 'urgency_description']
    .map(key => [key, (form[key] || '').trim()]))
  for (const key of ['location', 'contact', 'asset_id']) content[key] = (form[key] || '').trim() || null
  return { ...content, attachments: [...attachments] }
}
