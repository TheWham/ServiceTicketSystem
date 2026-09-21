package com.itticket.user.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

@Data
@Configuration
@ConfigurationProperties(prefix = "itticket.jwt")
public class JwtProperties {
    /** 必须与 gateway 一致;生产用环境变量 JWT_SECRET 或 Nacos 配置中心覆盖 */
    private String secret = "it-ticket-dev-jwt-secret-key-32bytes-minimum!!";
    private int ttlHours = 12;

    @Bean
    public BCryptPasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
