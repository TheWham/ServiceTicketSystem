package com.itticket.ticket.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

/**
 * 服务间内部建单请求(ai-service 人工客服转工单时调用)。
 * 与对外 CreateTicketRequest 的区别:由调用方指定 creatorId,不走网关透传头。
 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class InternalCreateRequest {
    /** 工单创建人(员工)ID */
    private String creatorId;
    private String title;
    private String category;
    private String description;
    private String priority;
    /** 幂等 token,ai-service 传 "ai-session-{会话ID}" 防止客服重复点击生成多单 */
    private String clientToken;
}
