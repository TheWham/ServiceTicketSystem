package com.itticket.rag.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.itticket.rag.entity.KnowledgeArticle;
import org.apache.ibatis.annotations.Mapper;

/**
 * knowledge_article 表访问层（MyBatis-Plus BaseMapper）。
 *
 * <p>表结构与乐观锁列见实体 {@link KnowledgeArticle} 头注释；
 * 状态迁移必须走 KnowledgeStore 的守卫方法（SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90），
 * 禁止绕过状态机直接 update。</p>
 */
@Mapper
public interface KnowledgeArticleMapper extends BaseMapper<KnowledgeArticle> {
}
