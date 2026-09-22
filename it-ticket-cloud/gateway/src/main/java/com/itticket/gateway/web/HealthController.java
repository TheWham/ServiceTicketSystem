package com.itticket.gateway.web;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.Map;

/** 网关自身健康检查,响应格式与旧版一致 */
@RestController
public class HealthController {

    @GetMapping("/api/health")
    public Map<String, Object> health() {
        return Map.of("status", "ok", "timestamp", Instant.now().toString());
    }
}
