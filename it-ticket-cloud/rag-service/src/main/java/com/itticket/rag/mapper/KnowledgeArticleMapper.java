package com.itticket.rag.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.toolkit.Constants;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itticket.rag.entity.KnowledgeArticle;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

/**
 * knowledge_article 表访问层（MyBatis-Plus BaseMapper）。
 *
 * <p>表结构与乐观锁列见实体 {@link KnowledgeArticle} 头注释；
 * 状态迁移必须走 KnowledgeStore 的守卫方法（SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90），
 * 禁止绕过状态机直接 update。</p>
 */
@Mapper
public interface KnowledgeArticleMapper extends BaseMapper<KnowledgeArticle> {
    /** 一次查询投影当前版本标题；按主键读取版本，不把正文返回列表。 */
    @Select("""
        SELECT a.*, COALESCE((
            SELECT CASE WHEN JSON_TYPE(JSON_EXTRACT(v.content, '$.title')) = 'STRING'
                THEN NULLIF(TRIM(JSON_UNQUOTE(JSON_EXTRACT(v.content, '$.title'))), '') END
            FROM knowledge_version v
            WHERE v.version_id = a.current_version_id AND v.article_id = a.article_id
        ), '（未命名知识）') AS title
        FROM knowledge_article a
        ${ew.customSqlSegment}
        """)
    Page<KnowledgeArticle> selectPageWithTitles(Page<KnowledgeArticle> page,
                                              @Param(Constants.WRAPPER) Wrapper<KnowledgeArticle> wrapper);
}
