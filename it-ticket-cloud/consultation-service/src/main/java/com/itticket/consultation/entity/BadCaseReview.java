package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * AI 拒答案例处置记录(对应表 bad_case_review,V2_6)。
 * 只存处置决策;待处置列表由 consultation_message 实时联查得出,本表 UNIQUE(ai_message_id)
 * 保证一条拒答只能处置一次。
 */
@Data
@TableName("bad_case_review")
public class BadCaseReview {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    private String aiMessageId;
    private String sessionId;
    private String interactionId;
    private String questionText;
    private String refusalReason;
    private BigDecimal confidence;
    /** GOLDEN_QA / GOLDEN_REFUSAL / DISCARD */
    private String decision;
    private Long goldenCaseId;
    private String reviewNote;
    private String reviewedBy;
    private LocalDateTime reviewedAt;
}
