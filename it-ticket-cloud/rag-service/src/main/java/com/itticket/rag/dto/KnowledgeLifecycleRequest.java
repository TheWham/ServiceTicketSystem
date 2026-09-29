package com.itticket.rag.dto;

import lombok.Data;

/**
 * ============================================================================
 * 知识生命周期动作请求体 (KnowledgeLifecycleRequest)
 * ============================================================================
 *
 * 【契约规范说明 (SM-KNOWLEDGE-001)】：
 * 四个动作复用同一请求体，各端点按需校验字段：
 * <ul>
 *   <li>提交审核 submit —— remark 选填</li>
 *   <li>发布 publish —— changeNote 选填（写入 knowledge_version.change_note）</li>
 *   <li>驳回 reject —— reason 必填（写入 knowledge_version.reject_reason）</li>
 *   <li>下线 offline —— reason 必填</li>
 * </ul>
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
public class KnowledgeLifecycleRequest {

    /** 备注/提审说明（最长 500） */
    private String remark;

    /** 原因（驳回、下线必填，最长 500） */
    private String reason;

    /** 版本变更说明（发布时写入 change_note，最长 500） */
    private String changeNote;
}
