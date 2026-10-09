package com.itticket.consultation.service;

import com.itticket.consultation.dto.KnowledgeHit;
import com.itticket.consultation.dto.KnowledgeSearchItem;
import com.itticket.consultation.dto.KnowledgeSearchResponse;
import com.itticket.consultation.mapper.KnowledgeQueryMapper;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

/**
 * 知识检索读模型(AI-API-005 知识搜索 + RAG 召回的唯一数据入口)。
 *
 * <p>唯一可见性口径:{@code knowledge_article.status='PUBLISHED'} 且
 * {@code knowledge_version.version_id = knowledge_article.current_version_id}
 * (AI-001、AI-API-005、RD-006「不检索已下线版本」)。口径写在
 * {@link KnowledgeQueryMapper} 的每条 SQL 里,本类不再另开旁路查询,
 * 也不提供按 versionId 直接取内容的方法,避免绕过发布状态。
 *
 * <p>本类只读，不开启独立事务。RAG 工作线程的查询按自动提交执行；输出阶段的引用复核
 * 使用调用方已有的回答落库事务，通过当前读避开旧快照，并将版本共享锁保持到该事务提交。
 *
 * <p>安全:方法内不打印检索词与知识正文(AI-008、RD-013「不得记录令牌、完整聊天正文」)。
 */
@Service
public class KnowledgeQueryService {

    /** AI-004.4:pageSize 上界 100。 */
    private static final int MAX_PAGE_SIZE = 100;
    /** AI-004.4:pageSize 下界 1。 */
    private static final int MIN_PAGE_SIZE = 1;
    /** 召回条数硬上界,防止上游传入超大 topK 拖垮检索(RD-007 资源隔离)。 */
    private static final int MAX_TOP_K = 50;
    /** AI-004.3:引用 title 最长 200。 */
    private static final int TITLE_MAX = 200;
    /** AI-004.4:搜索结果 summary 最长 2000。 */
    private static final int SUMMARY_MAX = 2000;
    /** 标题缺失时的占位:Schema 要求 title minLength=1。 */
    private static final String TITLE_PLACEHOLDER = "(未命名知识)";
    /** LIKE 通配符转义符。不用反斜杠,避免 MySQL 字符串层与 LIKE 层双重转义。 */
    private static final char LIKE_ESCAPE = '/';

    private final KnowledgeQueryMapper knowledgeQueryMapper;

    public KnowledgeQueryService(KnowledgeQueryMapper knowledgeQueryMapper) {
        this.knowledgeQueryMapper = knowledgeQueryMapper;
    }

    /**
     * AI-API-005 {@code GET /api/v1/knowledge/search}。
     *
     * <p>只返回 {@code PUBLISHED} 当前版本的 {@code articleId/versionId/title/summary/categoryId}
     * 与分页元数据,不暴露来源工单、作者、审核人与正文(AI-004.4)。
     *
     * @param query      检索词,可为 null/空白;为空时按发布时间倒序列出已发布知识
     * @param categoryId 分类过滤,可为 null/空白
     * @param page       页码,小于 1 按 1 处理
     * @param pageSize   每页条数,裁剪到 [1,100]
     * @return 永不为 null;越界页返回空 items 与真实 total
     */
    public KnowledgeSearchResponse search(String query, String categoryId, int page, int pageSize) {
        int safePage = Math.max(1, page);
        int safeSize = Math.min(MAX_PAGE_SIZE, Math.max(MIN_PAGE_SIZE, pageSize));
        String keyword = normalize(query);
        String pattern = likePattern(keyword);
        String category = normalize(categoryId);

        long total = knowledgeQueryMapper.countSearch(keyword, pattern, category);
        // 用 long 计算偏移量,避免 page 过大时 int 溢出成负数
        long offset = (long) (safePage - 1) * safeSize;
        if (total <= 0 || offset >= total) {
            return new KnowledgeSearchResponse(List.of(), safePage, safeSize, Math.max(0, total));
        }

        List<KnowledgeHit> rows =
                knowledgeQueryMapper.searchPage(keyword, pattern, category, (int) offset, safeSize);
        List<KnowledgeSearchItem> items = new ArrayList<>();
        if (rows != null) {
            for (KnowledgeHit row : rows) {
                items.add(new KnowledgeSearchItem(
                        row.getArticleId(),
                        row.getVersionId(),
                        truncate(blankToNull(row.getTitle()) == null ? TITLE_PLACEHOLDER : row.getTitle(), TITLE_MAX),
                        truncate(row.getSummary() == null ? "" : row.getSummary(), SUMMARY_MAX),
                        row.getCategoryId()));
            }
        }
        return new KnowledgeSearchResponse(List.copyOf(items), safePage, safeSize, total);
    }

    /**
     * RAG 召回:取 topK 条已发布当前版本知识。
     *
     * <p>先走 ngram 全文索引({@code MATCH ... AGAINST ... IN NATURAL LANGUAGE MODE});
     * 命中为空时退回 LIKE 模糊匹配,保证短词/低频词不至于直接无召回(RD-006
     * 「索引滞后时使用最后一个已知有效索引」的一期近似:两条路径读的都是同一张当前版本表)。
     *
     * @param query      检索词;null/空白直接返回空列表(无检索条件不得盲目召回)
     * @param categoryId 分类过滤,可为 null
     * @param topK       召回条数,裁剪到 [1,50]
     * @return 永不为 null,按相关度倒序
     */
    public List<KnowledgeHit> retrieve(String query, String categoryId, int topK) {
        String keyword = normalize(query);
        if (keyword == null) {
            return List.of();
        }
        int limit = Math.min(MAX_TOP_K, Math.max(1, topK));
        String category = normalize(categoryId);

        List<KnowledgeHit> hits = knowledgeQueryMapper.retrieveByFulltext(keyword, category, limit);
        if (hits == null || hits.isEmpty()) {
            hits = knowledgeQueryMapper.retrieveByLike(likePattern(keyword), category, limit);
        }
        return hits == null ? List.of() : hits;
    }

    /**
     * 引用有效性复核(AI-008:模型输出必须先通过「引用存在性 + 知识版本仍为 PUBLISHED」校验再返回客户端)。
     *
     * @return 文章为 PUBLISHED 且该版本就是当前版本时返回 true;任一入参为空返回 false
     */
    public boolean isPublishedCurrentVersion(String articleId, String versionId) {
        String article = normalize(articleId);
        String version = normalize(versionId);
        if (article == null || version == null) {
            return false;
        }
        return version.equals(knowledgeQueryMapper.selectPublishedCurrentVersion(article, version));
    }

    /** 去空白;空白视为「未提供」。 */
    private static String normalize(String value) {
        return blankToNull(value) == null ? null : value.trim();
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value;
    }

    /**
     * 构造 LIKE 中间串:转义 {@code /}、{@code %}、{@code _},配合 SQL 里的 {@code ESCAPE '/'},
     * 防止用户输入的通配符扩大匹配范围(RD-009 输入防御)。
     */
    private static String likePattern(String keyword) {
        if (keyword == null) {
            return null;
        }
        StringBuilder sb = new StringBuilder(keyword.length() + 8);
        for (int i = 0; i < keyword.length(); i++) {
            char c = keyword.charAt(i);
            if (c == LIKE_ESCAPE || c == '%' || c == '_') {
                sb.append(LIKE_ESCAPE);
            }
            sb.append(c);
        }
        return sb.toString();
    }

    private static String truncate(String value, int max) {
        if (value == null) {
            return null;
        }
        return value.length() <= max ? value : value.substring(0, max);
    }
}
