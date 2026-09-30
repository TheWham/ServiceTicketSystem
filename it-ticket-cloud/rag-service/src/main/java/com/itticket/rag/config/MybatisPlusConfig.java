package com.itticket.rag.config;

import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.OptimisticLockerInnerInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * ============================================================================
 * MyBatis-Plus 插件配置 (MybatisPlusConfig)
 * ============================================================================
 *
 * 【契约规范说明】（路径相对仓库根目录 docs/）：
 * 1. 乐观锁：实体使用 Long version，更新时把 version 放入 WHERE 条件并递增；
 *    MyBatis-Plus 必须注册 OptimisticLockerInnerInterceptor 才会真正生效
 *    （SM-001 · specs/03-business-state-machine.md:12；SQL-010 · specs/06-mysql-ddl-and-migrations.md:202）。
 * 2. 分页：知识列表与搜索接口使用物理分页。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Configuration
public class MybatisPlusConfig {

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        interceptor.addInnerInterceptor(new PaginationInnerInterceptor());
        interceptor.addInnerInterceptor(new OptimisticLockerInnerInterceptor());
        return interceptor;
    }
}
