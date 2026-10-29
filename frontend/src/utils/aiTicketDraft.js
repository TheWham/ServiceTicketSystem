/**
 * AI 拟好的建单草稿，从聊天页带到提单页。
 *
 * **为什么不复用 `GET /consultations/{id}/ticket-draft`**（那个接口本来就在，看起来正合适）：
 * 它是「按整条会话时间线起草」——标题取员工说过的**第一句**、描述取**整段对话摘要**，
 * 服务于「从咨询发起建单」这条老路径。而草稿卡上的内容是 agent 的 `prepare_ticket` 按
 * **当前这句话**拟的。两者不是一回事：直接复用会让员工点「编辑」后看到一串与卡片无关的
 * 旧对话内容，会话聊得越久偏得越离谱（实测踩到过）。
 *
 * **为什么用 sessionStorage 而不是 URL query**：描述上限 5000 字，塞进地址栏会超长，
 * 而且会进浏览器历史与访问日志。
 *
 * 仓库里已有约定：查询参数承载不了的大块上下文走客户端暂存，不要为了传参新增后端接口。
 * 这里带上 `sessionId` 并在读取时比对，避免一个会话的草稿被另一个会话误用；
 * 读取即消费，避免下次手动提单时被旧草稿顶上。
 */

const KEY = 'ai_ticket_draft'

/** 暂存一份 AI 草稿（点「编辑」时调用）。sessionStorage 不可用时静默跳过，提单页会退回服务端预填。 */
export function saveAiTicketDraft(sessionId, draft) {
  if (!sessionId || !draft) return
  try {
    sessionStorage.setItem(KEY, JSON.stringify({
      sessionId,
      title: String(draft.title || ''),
      description: String(draft.description || ''),
      category: String(draft.category || ''),
      priority: String(draft.priority || '')
    }))
  } catch { /* 隐私模式 / 存储配额满：跳过，不影响导航 */ }
}

/**
 * 读取**并清除**同会话的草稿；会话不匹配或解析失败返回 null。
 *
 * 「读取即清除」是刻意的：这份草稿只服务于紧接着的那一次「编辑」跳转。
 * 留着它会让员工下次手动提单时被一份早已过期的 AI 草稿顶上。
 */
export function takeAiTicketDraft(sessionId) {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (raw === null) return null
    sessionStorage.removeItem(KEY)
    if (!sessionId) return null
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || parsed.sessionId !== sessionId) return null
    return parsed
  } catch { return null }
}