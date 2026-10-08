package com.itticket.rag;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * ============================================================================
 * RAG 知识库服务启动类 (rag-service)
 * ============================================================================
 *
 * 【模块职责边界】：
 * 本模块负责知识入库（解析/切片/向量化/索引）、知识生命周期状态机
 * （SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90）与检索出口
 * （POST /api/v1/rag/retrievals，MR-004 · specs/10-model-rag-integration.md:70）。
 * 大模型生成、AI 会话与知识搜索契约接口（AI-API-002 / AI-API-005）由 AI 客服服务负责。
 */
@SpringBootApplication
@EnableDiscoveryClient
@EnableScheduling
@MapperScan("com.itticket.rag.mapper")
public class RagApplication {
    public static void main(String[] args) {
        SpringApplication.run(RagApplication.class, args);
    }
}
