package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.mapper.TicketMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

/**
 * 工单号生成:TK + yyyyMMdd + 4位自增(查当日最大号 + 1)。
 * 注意:日期必须用本地时区(与旧版注释一致),并发撞号由调用方捕获主键冲突后重试。
 */
@Component
@RequiredArgsConstructor
public class TicketNoGenerator {

    private static final DateTimeFormatter DAY = DateTimeFormatter.ofPattern("yyyyMMdd");

    private final TicketMapper ticketMapper;

    public String generate() {
        String prefix = "TK" + LocalDate.now().format(DAY);
        QueryWrapper<Ticket> qw = new QueryWrapper<>();
        qw.select("ticket_id").likeRight("ticket_id", prefix).orderByDesc("ticket_id").last("LIMIT 1");
        Ticket last = ticketMapper.selectOne(qw);
        int seq = 1;
        if (last != null && last.getTicketId().length() >= 4) {
            try {
                seq = Integer.parseInt(last.getTicketId().substring(last.getTicketId().length() - 4)) + 1;
            } catch (NumberFormatException ignored) {
                // 尾部非数字,从 1 开始
            }
        }
        return prefix + String.format("%04d", seq);
    }
}
