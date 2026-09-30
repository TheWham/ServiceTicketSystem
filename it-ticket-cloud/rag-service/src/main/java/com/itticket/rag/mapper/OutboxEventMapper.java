package com.itticket.rag.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.itticket.rag.entity.OutboxEvent;
import org.apache.ibatis.annotations.Mapper;

/**
 * outbox_event 领域事件表访问层（MyBatis-Plus BaseMapper）。
 *
 * <p>信封结构与写入约束见实体 {@link OutboxEvent} 头注释
 * （EV-001 · specs/07-domain-events-outbox-redis.md:12；
 * EV-008 · :85：同一聚合 aggregate_version 单调递增）。</p>
 */
@Mapper
public interface OutboxEventMapper extends BaseMapper<OutboxEvent> {
}
