package com.itticket.ticket.service;

import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.enums.TicketStatus;
import java.util.Objects;

/** 撤回档案由提单员工和平台管理员查看，工程师不再访问。 */
public final class TicketVisibility {
    private TicketVisibility() {}

    public static void checkRead(UserContext.CurrentUser viewer, Ticket ticket) {
        if (ticket == null) throw new BizException(ErrorCode.TICKET_NOT_FOUND);
        if (ticket.getStatus() == TicketStatus.CANCELLED
                && !"PLATFORM_ADMIN".equals(viewer.getRole())
                && !("EMPLOYEE".equals(viewer.getRole()) && Objects.equals(viewer.getUserId(), ticket.getCreatorId()))) {
            throw new BizException(ErrorCode.TICKET_NOT_FOUND, "工单不存在或不可见");
        }
    }
}
