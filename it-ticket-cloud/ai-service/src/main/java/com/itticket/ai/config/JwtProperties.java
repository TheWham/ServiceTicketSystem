package com.itticket.ai.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/** JWT 配置(与 gateway/user-service 共用同一 secret,用于 WebSocket 握手鉴权) */
@Data
@Configuration
@ConfigurationProperties(prefix = "itticket.jwt")
public class JwtProperties {
    private String secret;
}
