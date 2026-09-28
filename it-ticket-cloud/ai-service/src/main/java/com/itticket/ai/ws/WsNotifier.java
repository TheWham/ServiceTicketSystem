package com.itticket.ai.ws;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import java.io.IOException;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArraySet;

/**
 * WebSocket 连接注册中心(纯连接管理,不含业务逻辑):
 * - 按会话ID分组的连接(员工 + 接入客服双向实时收发)
 * - 在线客服连接集合(队列变动时广播提醒)
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class WsNotifier {

    private final ObjectMapper objectMapper;

    /** 会话ID → 该会话的所有在线连接 */
    private final Map<Long, Set<WebSocketSession>> sessionSockets = new ConcurrentHashMap<>();
    /** 全部在线客服连接(用于队列广播) */
    private final Set<WebSocketSession> agentSockets = new CopyOnWriteArraySet<>();

    /** 注册连接;role=customer_service 时同时加入客服广播组 */
    public void register(Long sessionId, WebSocketSession socket, String role) {
        if (sessionId != null) {
            sessionSockets.computeIfAbsent(sessionId, k -> new CopyOnWriteArraySet<>()).add(socket);
        }
        if ("customer_service".equals(role)) {
            agentSockets.add(socket);
        }
    }

    public void unregister(WebSocketSession socket) {
        sessionSockets.values().forEach(set -> set.remove(socket));
        agentSockets.remove(socket);
    }

    /** 向某会话的全部在线连接推送(系统消息、状态变更等) */
    public void sendToSession(Long sessionId, Object payload) {
        Set<WebSocketSession> sockets = sessionSockets.get(sessionId);
        if (sockets == null) {
            return;
        }
        broadcast(sockets, payload, null);
    }

    /**
     * 向某会话内除 exclude 外的连接推送(聊天消息:发送方本地已回显,不再重复推)
     */
    public void sendToSessionExcept(Long sessionId, Object payload, WebSocketSession exclude) {
        Set<WebSocketSession> sockets = sessionSockets.get(sessionId);
        if (sockets == null) {
            return;
        }
        broadcast(sockets, payload, exclude);
    }

    /** 提醒所有在线客服刷新队列(新会话排队/被接入/结束时调用) */
    public void notifyAgentsQueue() {
        broadcast(agentSockets, Map.of("type", "queue"), null);
    }

    private void broadcast(Set<WebSocketSession> sockets, Object payload, WebSocketSession exclude) {
        String text;
        try {
            text = objectMapper.writeValueAsString(payload);
        } catch (Exception e) {
            log.warn("[WS] 消息序列化失败: {}", e.getMessage());
            return;
        }
        for (WebSocketSession socket : sockets) {
            if (socket == exclude || !socket.isOpen()) {
                continue;
            }
            try {
                synchronized (socket) {   // 同一连接并发写需串行
                    socket.sendMessage(new TextMessage(text));
                }
            } catch (IOException e) {
                log.warn("[WS] 推送失败: {}", e.getMessage());
            }
        }
    }
}
