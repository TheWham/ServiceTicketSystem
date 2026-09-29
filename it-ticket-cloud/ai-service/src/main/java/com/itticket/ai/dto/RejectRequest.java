package com.itticket.ai.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

/** 客服驳回请求 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class RejectRequest {
    /** 驳回原因(必填,会写入会话并告知员工) */
    private String reason;
}
