package com.itticket.rag.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.itticket.rag.entity.KnowledgeTransition;
import org.apache.ibatis.annotations.Mapper;

/**
 * knowledge_transition 流转审计表访问层（MyBatis-Plus BaseMapper）。
 *
 * <p>只增不改：每次合法状态迁移追加一条记录，历史不可覆盖
 * （SM-001 · specs/03-business-state-machine.md:12）。</p>
 */
@Mapper
public interface KnowledgeTransitionMapper extends BaseMapper<KnowledgeTransition> {
}
