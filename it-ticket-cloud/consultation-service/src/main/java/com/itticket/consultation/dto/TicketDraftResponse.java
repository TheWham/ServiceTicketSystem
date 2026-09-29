package com.itticket.consultation.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;

/**
 * OpenAPI 05 getTicketDraftFromConsultation 的预填数据。
 *
 * <p>05 未为该接口定义专用 Schema(成功响应是通用 Envelope),字段按 PRD 9.1 第 3 条
 * 「AI 或人工咨询可预填标题、分类、描述、附件及会话摘要」给出;snake_case 与 05 系列一致。
 * 预填仅供员工确认修改,不得静默代替员工提交。
 */
@JsonPropertyOrder({"session_id", "status", "category_id", "convert_allowed", "title", "description", "summary"})
public record TicketDraftResponse(
        @JsonProperty("session_id") String sessionId,
        String status,
        @JsonProperty("category_id") String categoryId,
        @JsonProperty("convert_allowed") boolean convertAllowed,
        String title,
        String description,
        String summary) {
}
