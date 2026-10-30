# -*- coding: utf-8 -*-
"""一次性修块：用精确文本替换 TicketService 里被 patch 工具漂移的区块。

前两次尝试（补丁工具、花括号启发式重排）都会累积缩进漂移，
这里改为按行区间整体替换为手写好的精确文本，幂等、可重复执行。
"""
import io

P = (r"C:\Users\Admin\.wpscomate\agent\workspace\it-ticket-system"
     r"\it-ticket-cloud\ticket-service\src\main\java\com\itticket\ticket\service\TicketService.java")

BLOCK = '''    /**
     * 创建后后处理（事务提交后异步）：SLA 起算（§11.2）+ 自动路由发起（F-06）。
     * 自动路由只产出<b>待确认派单草案</b>，工单保持 NEW，由 confirmDispatch 在
     * 审批人确认后置 ASSIGNED 并通知工程师 —— 见 DispatchDraftService（HITL 写操作门禁）。
     * 路由失败：RoutingService 已落异常队列，工单保持 NEW 待管理员处理。
     */
    private void afterCreate(String ticketId) {
        try {
            Ticket ticket = ticketMapper.selectById(ticketId);
            if (ticket == null || ticket.getStatus() != TicketStatus.NEW) {
                return;
            }
            // 1. SLA 起算（完成 SLA 创建起算，新单默认 MEDIUM）


            // 2. 自动路由 —— 只挂草案，不落分派（需求归因文档:50 强制 HITL）
            routingService.route(ticket);
        } catch (Exception e) {
            log.error("[TICKET] 创建后处理失败: " + ticketId, e);
        }
    }

    /**
     * 确认派单草案 —— 门禁的<b>唯一放行执行点</b>。
     *
     * <p>审批人对草案 approve 后（DispatchDraftService.decide 判定通过）由
     * DispatchDraftController 调用本方法，真正落分派：
     * 写 assignment、NEW → ASSIGNED、记流转日志、通知工程师。
     * 事务由调用方（DispatchDraftService.decide）持有，本方法不再自开事务。
     *
     * <p>这里重新校验工单当前状态而不是信任调用方：草案可能在挂起期间因用户撤回、
     * 重复建单合并等原因离开 NEW；此时必须拒绝放行并抛出，不允许把
     * ASSIGNED 写到一个已终态的工单上。
     *
     * @throws BizException 工单不存在或已不是 NEW（草案失效，需驳回后重路由）
     */
    public void confirmDispatch(String draftId) {
        DispatchDraft draft = dispatchDraftService.getById(draftId);
        if (draft == null) {
            throw new BizException(ErrorCode.TICKET_NOT_FOUND, "派单草案不存在");
        }
        String ticketId = draft.getTicketId();
        Ticket ticket = ticketMapper.selectOne(new QueryWrapper<Ticket>()
                .eq("ticket_id", ticketId).last("FOR UPDATE"));
        if (ticket == null) {
            throw new BizException(ErrorCode.TICKET_NOT_FOUND, "工单不存在");
        }
        if (ticket.getStatus() != TicketStatus.NEW) {
            throw new BizException(ErrorCode.STATE_CONFLICT,
                    "工单当前状态为 " + ticket.getStatus() + "，该派单草案已失效");
        }
        routingService.assign(ticket, draft.getEngineerId());
        insertFlowLog(ticketId, TicketStatus.NEW.getValue(), TicketStatus.ASSIGNED.getValue(),
                "TICKET_ASSIGN", "PLATFORM_ADMIN",
                "审批人确认派单草案 " + draftId + "，分配工程师: " + draft.getEngineerId());
        notificationService.sendNotification(ticketId, "ASSIGNED", draft.getEngineerId());
    }

    private Collection<String> collectUserIds(List<Ticket> tickets) {'''

with io.open(P, encoding="utf-8", newline="") as f:
    lines = f.read().split("\r\n")

start = end = None
for i, ln in enumerate(lines):
    if i > 880 and start is None and ln.strip() == "/**":
        start = i
    if start is not None and ln.strip().startswith("private Collection<String> collectUserIds"):
        end = i
        break

assert start is not None and end is not None, (start, end)
new = BLOCK.split("\n")
lines[start:end + 1] = new

with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\r\n".join(lines))

print("replaced %d..%d with %d lines" % (start, end, len(new)))