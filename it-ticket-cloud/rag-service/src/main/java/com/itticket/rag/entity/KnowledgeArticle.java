package com.itticket.rag.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.Version;
import com.itticket.rag.enums.KnowledgeRiskLevel;
import com.itticket.rag.enums.KnowledgeStatus;
import lombok.Data;

/**
 * ============================================================================
 * 知识库文章实体 (KnowledgeArticle) - 对应数据库表 `knowledge_article`
 * ============================================================================
 *
 * 【契约规范说明 (DM-003 / DM 契约)】：
 * 1. 业务主键：不可变字符串业务 ID（如 "art-1718000000000"）。
 * 2. 状态生命周期：DRAFT (草稿) -> SUBMITTED (提交) -> REVIEWED (已审) -> PUBLISHED (已发布) -> ARCHIVED (已归档)。
 * 3. 乐观锁机制：由 Long version 字段控制，保障并发更新一致性。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@TableName("knowledge_article")
public class KnowledgeArticle {
    /** 知识文章业务主键 ID */
    @TableId(value = "article_id", type = IdType.INPUT)
    private String articleId;

    /** 文章当前发布/流转状态 */
    private KnowledgeStatus status;

    /** 当前生效/发布的版本 ID (关联 knowledge_version.version_id) */
    private String currentVersionId;

    /** 知识所属业务分类 ID (如 C_NET, C_SW, C_HW 等) */
    private String categoryId;

    /** 知识风险等级 (LOW-常规指导, MEDIUM-涉及系统配置, HIGH-高风险运维) */
    private KnowledgeRiskLevel riskLevel;

    /** 乐观锁版本号 (更新时自增) */
    @Version
    private Long version;
}
