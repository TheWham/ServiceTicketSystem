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
 * - 当日无单 -> 0001
 * - 当日最大单号尾部混入非数字（历史导入脏数据）-> 回退 0001，不崩溃
 * - 正常递增
 *
 * 单号格式：TK + yyyyMMdd + 4 位日序号，如 TK202609300001。
 * 取当日最大单号 +1；若历史数据尾部无法解析为数字，宁可回到 0001
 * （可能撞唯一约束而由调用方重试）也绝不能抛出未受控异常导致建单 500。
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

    /** 当日尚无工单：从 0001 起步 */
    @Test
    void emptyDayStartsAtOne() {
        when(ticketMapper.selectOne(any())).thenReturn(null);
        assertEquals(prefix + "0001", generator.generate());
    }

    /** 尾部完全非数字（如迁移工具标记 DROP）：解析失败回退 0001 */
    @Test
    void legacyJunkTailResetsToOne() {
        when(ticketMapper.selectOne(any())).thenReturn(withId(prefix + "DROP"));
        assertEquals(prefix + "0001", generator.generate());
    }

    /** 尾部混入字母（如人工修数写错）：同样回退 0001，不允许 NumberFormatException 冒出 */
    @Test
    void nonDigitMixResetsToOne() {
        when(ticketMapper.selectOne(any())).thenReturn(withId(prefix + "00A1"));
        assertEquals(prefix + "0001", generator.generate());
    }

    /** 正常路径：当日最大 0042 -> 生成 0043 */
    @Test
    void normalSequenceIncrements() {
        when(ticketMapper.selectOne(any())).thenReturn(withId(prefix + "0042"));
        assertEquals(prefix + "0043", generator.generate());
    }
}