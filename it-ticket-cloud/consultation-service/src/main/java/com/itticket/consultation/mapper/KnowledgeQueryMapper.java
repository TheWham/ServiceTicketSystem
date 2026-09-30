package com.itticket.consultation.mapper;

import com.itticket.consultation.dto.KnowledgeHit;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 知识检索只读查询(AI-API-005 知识搜索 + RAG 召回)。
 *
 * <p>全部查询强制同一口径:{@code knowledge_article.status='PUBLISHED'} 且
 * {@code knowledge_version.version_id = knowledge_article.current_version_id}
 * (AI-001「只读取当前 PUBLISHED 知识版本」、AI-API-005「只返回 PUBLISHED」、
 * RD-006「不检索已下线版本」)。文章一旦下线或切换当前版本,旧版本立刻不可召回。
 *
 * <p>SQL 显式列出列名,不使用 {@code SELECT *}(DM-004 同口径);所有变量走 {@code #{}} 预编译参数,
 * 不做字符串拼接。不返回 {@code author_id}、{@code reviewer_id}、{@code change_note} 等
 * 非检索字段,也不暴露来源工单(AI-004.4)。
 *
 * <p>本接口不继承 {@code BaseMapper}:它只做跨表只读投影,不需要单表 CRUD。
 */
@Mapper
public interface KnowledgeQueryMapper {

    /**
     * RAG 召回:ngram 全文索引自然语言检索,按相关度取前 N 条。
     *
     * @param keyword    检索词,非空非空白
     * @param categoryId 可选分类过滤,null/空串表示不限
     * @param limit      取前 N 条,调用方已裁剪上下界
     */
    @Select("""
            <script>
            SELECT a.article_id                                            AS articleId,
                   v.version_id                                            AS versionId,
                   JSON_UNQUOTE(JSON_EXTRACT(v.content, '$.title'))   AS title,
                   JSON_UNQUOTE(JSON_EXTRACT(v.content, '$.summary')) AS summary,
                   JSON_UNQUOTE(JSON_EXTRACT(v.content, '$.body'))    AS body,
                   a.category_id                                           AS categoryId,
                   MATCH(v.search_text) AGAINST(#{keyword} IN NATURAL LANGUAGE MODE) AS score
              FROM knowledge_article a
              JOIN knowledge_version v
                ON v.version_id = a.current_version_id
               AND v.article_id = a.article_id
             WHERE a.status = 'PUBLISHED'
               AND MATCH(v.search_text) AGAINST(#{keyword} IN NATURAL LANGUAGE MODE)
            <if test="categoryId != null and categoryId != ''">
               AND a.category_id = #{categoryId}
            </if>
             ORDER BY score DESC, v.published_at DESC, v.version_id ASC
             LIMIT #{limit}
            </script>
            """)
    List<KnowledgeHit> retrieveByFulltext(@Param("keyword") String keyword,
                                          @Param("categoryId") String categoryId,
                                          @Param("limit") int limit);

    /**
     * RAG 召回回退:ngram 分词未命中(短词、低频词)时用 LIKE 模糊匹配兜底。
     *
     * <p>基础分为 {@code 1.0 / 名次}(名次按发布时间倒序,MySQL 8 窗口函数):
     * 首条经 {@code MySqlKnowledgeRetriever} 归一化后相关度为 0.5，低于
     * {@code ai.local-retrieval-min-score} 默认值 0.60，因此默认按 {@code LOW_CONFIDENCE} 拒答。
     * 这是本地检索可靠性策略，与模型回答置信度及语义知识冲突判定分别处理。
     *
     * @param pattern    已按 {@code ESCAPE '/'} 转义过的 LIKE 中间串(不含首尾百分号)
     * @param categoryId 可选分类过滤
     * @param limit      取前 N 条
     */
    @Select("""
            <script>
            SELECT a.article_id                                            AS articleId,
                   v.version_id                                            AS versionId,
                   JSON_UNQUOTE(JSON_EXTRACT(v.content, '$.title'))   AS title,
                   JSON_UNQUOTE(JSON_EXTRACT(v.content, '$.summary')) AS summary,
                   JSON_UNQUOTE(JSON_EXTRACT(v.content, '$.body'))    AS body,
                   a.category_id                                           AS categoryId,
                   1.0 / ROW_NUMBER() OVER (ORDER BY v.published_at DESC, v.version_id ASC) AS score
              FROM knowledge_article a
              JOIN knowledge_version v
                ON v.version_id = a.current_version_id
               AND v.article_id = a.article_id
             WHERE a.status = 'PUBLISHED'
               AND v.search_text LIKE CONCAT('%', #{pattern}, '%') ESCAPE '/'
            <if test="categoryId != null and categoryId != ''">
               AND a.category_id = #{categoryId}
            </if>
             ORDER BY v.published_at DESC, v.version_id ASC
             LIMIT #{limit}
            </script>
            """)
    List<KnowledgeHit> retrieveByLike(@Param("pattern") String pattern,
                                      @Param("categoryId") String categoryId,
                                      @Param("limit") int limit);

    /**
     * AI-API-005 知识搜索分页。关键词为空时退化为按发布时间倒序列出已发布知识。
     *
     * <p>关键词非空时同时接受全文命中与 LIKE 命中,排序以全文相关度为主键;
     * WHERE 条件与 {@link #countSearch} 完全一致,保证 total 与 items 不会互相矛盾。
     * 不查询 {@code body},搜索结果只返回 AI-004.4 允许的元数据字段。
     *
     * @param keyword    检索词,可为 null/空串
     * @param pattern    与 keyword 对应的 LIKE 转义串,keyword 为空时不参与渲染
     * @param categoryId 可选分类过滤
     * @param offset     偏移量,调用方保证非负且小于 total
     * @param limit      每页条数,调用方已裁剪到 1~100(AI-004.4)
     */
    @Select("""
            <script>
            SELECT a.article_id                                            AS articleId,
                   v.version_id                                            AS versionId,
                   JSON_UNQUOTE(JSON_EXTRACT(v.content, '$.title'))   AS title,
                   JSON_UNQUOTE(JSON_EXTRACT(v.content, '$.summary')) AS summary,
                   a.category_id                                           AS categoryId,
            <choose>
              <when test="keyword != null and keyword != ''">
                   MATCH(v.search_text) AGAINST(#{keyword} IN NATURAL LANGUAGE MODE) AS score
              </when>
              <otherwise>
                   0 AS score
              </otherwise>
            </choose>
              FROM knowledge_article a
              JOIN knowledge_version v
                ON v.version_id = a.current_version_id
               AND v.article_id = a.article_id
             WHERE a.status = 'PUBLISHED'
            <if test="keyword != null and keyword != ''">
               AND (MATCH(v.search_text) AGAINST(#{keyword} IN NATURAL LANGUAGE MODE)
                    OR v.search_text LIKE CONCAT('%', #{pattern}, '%') ESCAPE '/')
            </if>
            <if test="categoryId != null and categoryId != ''">
               AND a.category_id = #{categoryId}
            </if>
             ORDER BY score DESC, v.published_at DESC, v.version_id ASC
             LIMIT #{limit} OFFSET #{offset}
            </script>
            """)
    List<KnowledgeHit> searchPage(@Param("keyword") String keyword,
                                  @Param("pattern") String pattern,
                                  @Param("categoryId") String categoryId,
                                  @Param("offset") int offset,
                                  @Param("limit") int limit);

    /** AI-API-005 分页总数,WHERE 条件与 {@link #searchPage} 保持逐字一致。 */
    @Select("""
            <script>
            SELECT COUNT(1)
              FROM knowledge_article a
              JOIN knowledge_version v
                ON v.version_id = a.current_version_id
               AND v.article_id = a.article_id
             WHERE a.status = 'PUBLISHED'
            <if test="keyword != null and keyword != ''">
               AND (MATCH(v.search_text) AGAINST(#{keyword} IN NATURAL LANGUAGE MODE)
                    OR v.search_text LIKE CONCAT('%', #{pattern}, '%') ESCAPE '/')
            </if>
            <if test="categoryId != null and categoryId != ''">
               AND a.category_id = #{categoryId}
            </if>
            </script>
            """)
    long countSearch(@Param("keyword") String keyword,
                     @Param("pattern") String pattern,
                     @Param("categoryId") String categoryId);

    /**
     * 引用有效性复核(AI-008:返回客户端前必须确认引用的知识版本仍为 PUBLISHED 当前版本)。
     *
     * <p>锁定读获取最新提交状态，不复用 REPEATABLE READ 快照或 MyBatis 查询缓存。
     * 在回答落库事务中，共享锁持续到提交；竞争写锁时立即失败，由调用方明确降级。
     *
     * @return 当前发布版本 ID；不存在时为 null
     */
    @Options(useCache = false, flushCache = Options.FlushCachePolicy.TRUE)
    @Select("""
            SELECT v.version_id
              FROM knowledge_article a
              JOIN knowledge_version v
                ON v.version_id = a.current_version_id
               AND v.article_id = a.article_id
             WHERE a.status = 'PUBLISHED'
               AND a.article_id = #{articleId}
               AND v.version_id = #{versionId}
             FOR SHARE NOWAIT
            """)
    String selectPublishedCurrentVersion(@Param("articleId") String articleId,
                                         @Param("versionId") String versionId);
}
