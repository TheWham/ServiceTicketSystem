package com.itticket.rag.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.itticket.rag.entity.KnowledgeVersion;
import org.apache.ibatis.annotations.Mapper;

/**
 * knowledge_version 表访问层（MyBatis-Plus BaseMapper）。
 *
 * <p>版本快照不可变：发布后留痕，修改产生新版本
 * （SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90「新版本发布」迁移）；
 * content 列四键读写统一走 support/KnowledgeContent。</p>
 */
@Mapper
public interface KnowledgeVersionMapper extends BaseMapper<KnowledgeVersion> {
}
