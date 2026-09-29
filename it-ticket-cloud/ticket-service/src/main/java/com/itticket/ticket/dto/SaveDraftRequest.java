package com.itticket.ticket.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.Map;

/** spec 05 saveTicketDraft 请求体(Draft schema:payload 自由对象 + expires_at,无必填字段)。 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class SaveDraftRequest {
    /** 残缺字段也允许保存(PRD 10.4) */
    private Map<String, Object> payload;
    /** 缺省时服务端取保存时刻 +7 天 */
    private LocalDateTime expiresAt;
}
