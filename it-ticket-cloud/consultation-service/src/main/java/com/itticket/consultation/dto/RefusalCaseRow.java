package com.itticket.consultation.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/** 拒答联查行(Mapper 结果载体,列别名对齐属性)。 */
@Data
public class RefusalCaseRow {
    private String messageId;
    private String sessionId;
    private String questionText;
    private String refusalReason;
    private BigDecimal confidence;
    private LocalDateTime sentAt;
    /** PENDING / REVIEWED */
    private String reviewStatus;
    private String decision;
}
