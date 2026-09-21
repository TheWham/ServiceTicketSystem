package com.itticket.gateway.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "itticket.jwt")
public class JwtProperties {
    /** 与 user-service 保持一致;生产环境通过环境变量或 Nacos 配置中心下发 */
    private String secret = "it-ticket-dev-jwt-secret-key-32bytes-minimum!!";
}
