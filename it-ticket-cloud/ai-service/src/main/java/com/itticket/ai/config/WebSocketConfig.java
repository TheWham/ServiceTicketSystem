package com.itticket.ai.config;

import com.itticket.ai.ws.ChatWebSocketHandler;
import com.itticket.ai.ws.WsAuthInterceptor;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

/**
 * WebSocket 端点:/ws/ai/chat?token=xxx[&sessionId=xxx]
 * 网关以 lb:ws:// 路由 /ws/ai/** 到本服务;握手鉴权见 WsAuthInterceptor。
 */
@Configuration
@EnableWebSocket
@RequiredArgsConstructor
public class WebSocketConfig implements WebSocketConfigurer {

    private final ChatWebSocketHandler chatWebSocketHandler;
    private final WsAuthInterceptor wsAuthInterceptor;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(chatWebSocketHandler, "/ws/ai/chat")
                .addInterceptors(wsAuthInterceptor)
                .setAllowedOriginPatterns("*");   // 开发期跨域;握手本身有 token 鉴权
    }
}
