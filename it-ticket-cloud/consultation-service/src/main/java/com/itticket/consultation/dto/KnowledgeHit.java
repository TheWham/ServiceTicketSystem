package com.itticket.consultation.dto;

import lombok.Data;

/**
 * 知识检索命中投影(内部 DTO,不直接对外序列化)。
 *
 * <p>只承载 {@code PUBLISHED} 且为 {@code knowledge_article.current_version_id} 的版本内容
 * (AI-001、AI-API-005、RD-006「不检索已下线版本」);不包含来源工单、作者、审核人等字段,
 * 避免脱敏前的原始数据外泄(AI-008、AI-004.4)。
 *
 * <p>用普通类而非 record:MyBatis 自动映射按 setter 回填,列名与属性对应关系更稳
 * (record 需要 {@code @ConstructorArgs} 或构造器映射)。
 *
 * <p>{@code score} 是数据源的原始相关度:
 * <ul>
 *   <li>全文检索命中为 MySQL {@code MATCH ... AGAINST} 相关度,取值无上界;</li>
 *   <li>LIKE 回退命中为按名次衰减的基础分({@code 1/名次}),见 {@code KnowledgeQueryMapper}。</li>
 * </ul>
 * 对外(引用 score、置信度)必须先归一化到 [0,1] 并保留 4 位小数(AI-004.3),
 * 归一化在 {@code KnowledgeRagAdapter} 内完成。
 */
@Data
public class KnowledgeHit {

    /** knowledge_article.article_id */
    private String articleId;
    /** knowledge_version.version_id,恒等于文章的 current_version_id */
    private String versionId;
    /** content_json.$.title */
    private String title;
    /** content_json.$.summary */
    private String summary;
    /** content_json.$.body */
    private String body;
    /** knowledge_article.category_id */
    private String categoryId;
    /** 数据源原始相关度,非归一化值;SQL 保证非 NULL。 */
    private double score;
}
