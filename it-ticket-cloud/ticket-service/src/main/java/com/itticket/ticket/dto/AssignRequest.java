package com.itticket.ticket.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

/** 派单/改派请求 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class AssignRequest {
    private String assigneeId;
    private String reason;
}
