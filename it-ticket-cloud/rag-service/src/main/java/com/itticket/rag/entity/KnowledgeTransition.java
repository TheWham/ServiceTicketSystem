package com.itticket.rag.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * ============================================================================
 * 知识状态流转审计实体 (KnowledgeTransition) - 对应数据库表 `knowledge_transition`
 * ============================================================================
 *
 * 【契约规范说明】（路径相对仓库根目录 docs/）：
 * 1. 每个合法迁移必须追加一条流转记录，实体状态不可直接覆盖历史
 *    （SM-001 · specs/03-business-state-machine.md:12）。
 * 2. event_code 使用稳定的 DOMAIN_ACTION 动作码（如 KNOWLEDGE_SUBMIT_REVIEW / KNOWLEDGE_PUBLISH /
 *    KNOWLEDGE_REJECT / KNOWLEDGE_OFFLINE），不得与领域事实事件类型（SCREAMING_SNAKE_CASE）混用
 *    （SM-EVENT-001 · specs/03-business-state-machine.md:103）。
 * 3. 迁移守卫与角色要求见 SM-KNOWLEDGE-001（specs/03-business-state-machine.md:90）；
 *    驳回/下线必须携带非空 reason。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@TableName("knowledge_transition")
public class KnowledgeTransition {

    /** 流转记录业务 ID */
    @TableId(value = "transition_id", type = IdType.INPUT)
    private String transitionId;

    /** 知识文章业务 ID */
    private String articleId;

    /** 涉及的知识版本 ID（提交/发布/驳回/下线时通常非空） */
    private String versionId;

    /** 迁移前状态 */
    private String fromStatus;

    /** 迁移后状态 */
    private String toStatus;

    /** 触发迁移的业务动作码 (DOMAIN_ACTION) */
    private String eventCode;

    /** 操作人 User ID */
    private String operatorId;

    /** 操作人角色（网关透传值，如 KB_ADMIN / PLATFORM_ADMIN） */
    private String operatorRole;

    /** 原因或备注：驳回、下线必填 */
    private String reason;

    /** 迁移发生时间 */
    private LocalDateTime occurredAt;
}
