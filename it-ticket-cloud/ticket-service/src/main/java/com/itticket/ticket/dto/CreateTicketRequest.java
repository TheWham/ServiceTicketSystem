package com.itticket.ticket.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

import java.util.Map;

/**
 * spec 05 TicketCreate 建单请求(2026-09 新契约,替代旧版 title/category/priority 精简表单)。
 *
 * <p>必填六项:ticket_nature、category_id、title、description、impact_description、
 * urgency_description;选填 location、contact、asset_id、source_session_id、field_values。
 * 优先级不在请求中——PRD 11.4:新工单暂按中优先级,工程师接单时按矩阵确认正式优先级。
 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class CreateTicketRequest {
    /** INCIDENT 故障报修 / SERVICE_REQUEST 服务申请 */
    private String ticketNature;
    /** 启用的末级分类编号 */
    private String categoryId;
    private String title;
    private String description;
    private String impactDescription;
    private String urgencyDescription;
    private String location;
    private String contact;
    private String assetId;
    /** 来源咨询会话(CS 前缀,咨询转单时写入) */
    private String sourceSessionId;
    /** 分类扩展字段值快照(PRD 10.3) */
    private Map<String, Object> fieldValues;
}
