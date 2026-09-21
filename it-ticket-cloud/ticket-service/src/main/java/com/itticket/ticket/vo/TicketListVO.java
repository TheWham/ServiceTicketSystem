package com.itticket.ticket.vo;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.AllArgsConstructor;
import lombok.Data;

import java.util.List;

/** 工单分页响应,字段名与旧版一致 */
@Data
@AllArgsConstructor
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class TicketListVO {
    private List<TicketVO> list;
    private long total;
    private int page;
    private int pageSize;
}
