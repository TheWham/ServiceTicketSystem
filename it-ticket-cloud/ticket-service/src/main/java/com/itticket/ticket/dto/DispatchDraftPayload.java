package com.itticket.ticket.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 派单草案（dispatch_draft.payload_json）的结构化载荷。
 *
 * <p>对齐讲义 HITL 机制的结构化契约要求：草案必须可被审批人完整判读 ——
 * 建议给谁、依据是什么、候选还有谁、何时失效。审批人只据此决定放行或驳回，
 * 不存在「AI 自行改派」的路径。
 */
@Data
@JsonPropertyOrder({"draft_id", "ticket_id", "title", "priority", "category_id",
        "proposed_engineer_id", "proposed_engineer_name", "selection_note",
        "expires_at", "generated_at"})
public class DispatchDraftPayload {

    @JsonProperty("draft_id")
    private String draftId;
    @JsonProperty("ticket_id")
    private String ticketId;
    private String title;
    private String priority;
    @JsonProperty("category_id")
    private String categoryId;
    /** 草案建议的工程师 */
    @JsonProperty("proposed_engineer_id")
    private String proposedEngineerId;
    @JsonProperty("proposed_engineer_name")
    private String proposedEngineerName;
    /** 选人依据（分类路由 / 在线可用 / 负载），审批人据此判断是否改派 */
    @JsonProperty("selection_note")
    private String selectionNote;
    /** 草案失效时刻，对应讲义「专属 Token 含超时失效」 */
    @JsonProperty("expires_at")
    private LocalDateTime expiresAt;
    @JsonProperty("generated_at")
    private LocalDateTime generatedAt;
    /** 本轮候选工程师（按负载升序），审批人可据此改判 */
    private List<String> candidates;
}