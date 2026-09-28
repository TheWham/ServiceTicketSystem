package com.itticket.ai.ws;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.ai.entity.ChatMessage;
import com.itticket.ai.entity.ChatSession;
import com.itticket.ai.enums.SessionStatus;
import com.itticket.ai.mapper.ChatMessageMapper;
import com.itticket.ai.mapper.ChatSessionMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

/**
 * 人工客服实时聊天(WebSocket)。
 * 协议(均为 JSON 文本帧):
 *   客户端 → 服务端:{"type":"msg","session_id":1,"content":"..."}
 *   服务端 → 客户端:{"type":"msg","session_id":1,"sender_type":"USER|AGENT","sender_id":"U001",
 *                   "sender_name":"张小明","content":"...","create_time":"..."}
 * 发送方身份一律取握手时校验过的 attributes,不信任客户端传值。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ChatWebSocketHandler extends TextWebSocketHandler {

    private static final DateTimeFormatter DISPLAY = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final WsNotifier wsNotifier;
    private final ChatSessionMapper sessionMapper;
    private final ChatMessageMapper messageMapper;
    private final ObjectMapper objectMapper;

    @Override
    public void afterConnectionEstablished(WebSocketSession socket) {
        Long sessionId = (Long) socket.getAttributes().get("sessionId");
        String role = (String) socket.getAttributes().get("role");
        wsNotifier.register(sessionId, socket, role);
        log.info("[WS] 连接建立: user={}, role={}, session={}",
                socket.getAttributes().get("userId"), role, sessionId);
    }

    @Override
    protected void handleTextMessage(WebSocketSession socket, TextMessage message) throws Exception {
        JsonNode payload = objectMapper.readTree(message.getPayload());
        if (!"msg".equals(payload.path("type").asText())) {
            return;
        }
        Long sessionId = payload.path("session_id").asLong(0);
        String content = payload.path("content").asText("").trim();
        if (sessionId <= 0 || content.isEmpty() || content.length() > 1000) {
            return;
        }

        String userId = (String) socket.getAttributes().get("userId");
        String name = (String) socket.getAttributes().get("name");
        String role = (String) socket.getAttributes().get("role");

        // 会话状态与发送权限校验:必须处于人工阶段;员工须为会话发起人,客服须为已接入的客服
        ChatSession session = sessionMapper.selectById(sessionId);
        if (session == null) {
            sendError(socket, sessionId, "会话不存在");
            return;
        }
        if (session.getStatus() != SessionStatus.HUMAN_HANDLING
                && session.getStatus() != SessionStatus.WAITING_HUMAN) {
            sendError(socket, sessionId, "当前会话不在人工沟通阶段");
            return;
        }
        boolean isOwner = userId.equals(session.getUserId());
        boolean isAgent = "customer_service".equals(role);
        if (!isOwner && !isAgent) {
            sendError(socket, sessionId, "无权在该会话发言");
            return;
        }
        // 员工在客服接入前(排队中)发言无意义,提示等待
        if (isOwner && session.getStatus() == SessionStatus.WAITING_HUMAN) {
            sendError(socket, sessionId, "客服尚未接入，请稍候");
            return;
        }

        // 落库 + 广播给会话内其他连接(发送方本地已回显)
        String senderType = isAgent ? ChatMessage.SENDER_AGENT : ChatMessage.SENDER_USER;
        ChatMessage saved = new ChatMessage();
        saved.setSessionId(sessionId);
        saved.setSenderType(senderType);
        saved.setSenderId(userId);
        saved.setContent(content);
        messageMapper.insert(saved);

        // 发言方socket加入会话分组(客服接入后首次发言时其连接未带 sessionId)
        wsNotifier.register(sessionId, socket, role);

        Map<String, Object> out = new HashMap<>();
        out.put("type", "msg");
        out.put("session_id", sessionId);
        out.put("sender_type", senderType);
        out.put("sender_id", userId);
        out.put("sender_name", name == null ? userId : name);
        out.put("content", content);
        out.put("create_time", LocalDateTime.now().format(DISPLAY));
        wsNotifier.sendToSessionExcept(sessionId, out, socket);
    }

    @Override
    public void afterConnectionClosed(WebSocketSession socket, CloseStatus status) {
        wsNotifier.unregister(socket);
    }

    private void sendError(WebSocketSession socket, Long sessionId, String msg) throws Exception {
        Map<String, Object> error = Map.of(
                "type", "error",
                "session_id", sessionId,
                "content", msg);
        synchronized (socket) {
            socket.sendMessage(new TextMessage(objectMapper.writeValueAsString(error)));
        }
    }
}
