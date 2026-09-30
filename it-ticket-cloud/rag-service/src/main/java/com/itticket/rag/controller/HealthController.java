package com.itticket.rag.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * ============================================================================
 * 健康检查控制器 (HealthController)
 * ============================================================================
 *
 * 【用途】：供网关/运维探活，确认 rag-service 进程可用。
 * 不检查下游依赖（MySQL/ES），依赖可用性由各自调用链按降级策略处理
 * （RD-006 · specs/04-resilience-degradation.md:67）。
 */
@RestController
public class HealthController {

    /** GET /api/v1/health 之外的独立探活端点（网关注册中心健康检查用） */
    @GetMapping("/api/health")
    public Map<String, Object> health() {
        return Map.of(
                "status", "UP",
                "service", "rag-service",
                "timestamp", System.currentTimeMillis()
        );
    }
}
