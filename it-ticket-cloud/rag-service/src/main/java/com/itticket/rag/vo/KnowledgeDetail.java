package com.itticket.rag.vo;

import com.itticket.rag.entity.KnowledgeArticle;
import com.itticket.rag.entity.KnowledgeTransition;
import com.itticket.rag.entity.KnowledgeVersion;

import java.util.List;

/**
 * ============================================================================
 * 知识详情视图 (KnowledgeDetail)
 * ============================================================================
 *
 * <p>文章 + 当前版本 + 完整流转审计（SM-001 · specs/03-business-state-machine.md:12：
 * 状态不可覆盖历史，审计可回溯）。</p>
 *
 * @author IT工单系统研发组 - RAG专项
 */
public record KnowledgeDetail(
        KnowledgeArticle article,
        KnowledgeVersion currentVersion,
        List<KnowledgeTransition> transitions) {
}
