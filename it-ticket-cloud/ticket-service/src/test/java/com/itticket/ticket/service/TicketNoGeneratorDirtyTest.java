package com.itticket.ticket.service;

import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.mapper.TicketMapper;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * 单号生成对脏数据的兜底：
 * - 当日无单 → 0001
 * - 当日最大单号尾部混入非数字（历史导入脏数据）→ 回退 0001，不崩溃
 * - 正常递增
 */
class TicketNoGeneratorDirtyTest {

    private final TicketMapper ticketMapper = mock(TicketMapper.class);
    private final TicketNoGenerator generator = new TicketNoGenerator(ticketMapper);
    private final String prefix = "TK" + LocalDate.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"));

    private Ticket withId(String id) {
        Ticket t = new Ticket();
        t.setTicketId(id);
        return t;
    }

    @Test
    void emptyDayStartsAtOne() {
        when(ticketMapper.selectOne(any())).thenReturn(null);
        assertEquals(prefix + "0001", generator.generate());
    }

    @Test
    void legacyJunkTailResetsToOne() {
        when(ticketMapper.selectOne(any())).thenReturn(withId(prefix + "DROP"));
        assertEquals(prefix + "0001", generator.generate());
    }

    @Test
    void nonDigitMixResetsToOne() {
        when(ticketMapper.selectOne(any())).thenReturn(withId(prefix + "00A1"));
        assertEquals(prefix + "0001", generator.generate());
    }

    @Test
    void normalSequenceIncrements() {
        when(ticketMapper.selectOne(any())).thenReturn(withId(prefix + "0042"));
        assertEquals(prefix + "0043", generator.generate());
    }
}
