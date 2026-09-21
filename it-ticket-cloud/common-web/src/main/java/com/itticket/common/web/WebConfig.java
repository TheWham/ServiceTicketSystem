package com.itticket.common.web;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.util.ArrayList;
import java.util.List;

/**
 * 注册 UserContextInterceptor;免认证路径通过 itticket.auth.exclude-paths 配置。
 */
@Data
@ConfigurationProperties(prefix = "itticket.auth")
class AuthProperties {
    /** 免认证(免 UserContext)路径,Ant 风格 */
    private List<String> excludePaths = new ArrayList<>();
}

public class WebConfig implements WebMvcConfigurer {

    private final AuthProperties authProperties;
    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    public WebConfig(AuthProperties authProperties) {
        this.authProperties = authProperties;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new UserContextInterceptor())
                .addPathPatterns("/**")
                .excludePathPatterns(authProperties.getExcludePaths());
    }

    boolean isExcluded(String path) {
        return authProperties.getExcludePaths().stream().anyMatch(p -> pathMatcher.match(p, path));
    }
}
