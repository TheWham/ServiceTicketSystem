package com.itticket.ai.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.itticket.ai.entity.ChatMessage;
import com.itticket.ai.entity.ChatSession;
import com.itticket.ai.enums.SessionStatus;
import com.itticket.ai.feign.TicketClient;
import com.itticket.ai.mapper.ChatMessageMapper;
import com.itticket.ai.mapper.ChatSessionMapper;
import com.itticket.ai.ws.WsNotifier;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.api.Result;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 咨询会话服务:状态机流转 + 消息存取 + 转工单。
 * 状态图见 SessionStatus 注释;所有流转都校验来源状态,非法操作抛业务异常。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ChatSessionService {

    private final ChatSessionMapper sessionMapper;
    private final ChatMessageMapper messageMapper;
    private final TicketClient ticketClient;
    private final WsNotifier wsNotifier;

    // ---------------- 会话与消息查询 ----------------

    /** 新建会话(AI_HANDLING) */
    public ChatSession createSession(String userId) {
        ChatSession session = new ChatSession();
        session.setUserId(userId);
        session.setStatus(SessionStatus.AI_HANDLING);
        session.setResolved(0);
        sessionMapper.insert(session);
        return session;
    }

    /** 加载会话并校验归属(员工只能看自己的会话) */
    public ChatSession getOwnedSession(Long sessionId, String userId) {
        ChatSession session = sessionMapper.selectById(sessionId);
        if (session == null) {
            throw new BizException(ErrorCode.SESSION_NOT_FOUND);
        }
        if (!session.getUserId().equals(userId)) {
            throw new BizException(ErrorCode.FORBIDDEN, "无权访问该会话");
        }
        return session;
    }

    /** 加载会话(客服侧使用,不校验归属) */
    public ChatSession getSession(Long sessionId) {
        ChatSession session = sessionMapper.selectById(sessionId);
        if (session == null) {
            throw new BizException(ErrorCode.SESSION_NOT_FOUND);
        }
        return session;
    }

    public List<ChatSession> mySessions(String userId) {
        QueryWrapper<ChatSession> query = new QueryWrapper<>();
        query.eq("user_id", userId).orderByDesc("id").last("LIMIT 20");
        return sessionMapper.selectList(query);
    }

    public List<ChatMessage> listMessages(Long sessionId) {
        QueryWrapper<ChatMessage> query = new QueryWrapper<>();
        query.eq("session_id", sessionId).orderByAsc("id").last("LIMIT 200");
        return messageMapper.selectList(query);
    }

    /** 写消息并返回(WS 广播与 REST 共用) */
    public ChatMessage addMessage(Long sessionId, String senderType, String senderId, String content) {
        ChatMessage message = new ChatMessage();
        message.setSessionId(sessionId);
        message.setSenderType(senderType);
        message.setSenderId(senderId);
        message.setContent(content);
        messageMapper.insert(message);
        return message;
    }

    // ---------------- 员工侧流转 ----------------

    /** 员工反馈已解决 → RESOLVED,流程结束不生成工单 */
    public ChatSession resolveByUser(Long sessionId, String userId) {
        ChatSession session = getOwnedSession(sessionId, userId);
        if (session.getStatus() != SessionStatus.AI_HANDLING
                && session.getStatus() != SessionStatus.HUMAN_HANDLING) {
            throw new BizException(ErrorCode.PARAM_INVALID, "当前会话状态不支持该操作");
        }
        updateStatus(sessionId, SessionStatus.RESOLVED);
        sessionMapper.update(null, new UpdateWrapper<ChatSession>()
                .eq("id", sessionId).set("resolved", 1));
        addMessage(sessionId, ChatMessage.SENDER_SYSTEM, null, "员工确认问题已解决，会话结束");
        // 人工阶段客服在线时,实时通知客服会话已关闭
        wsNotifier.sendToSession(sessionId, systemPayload(sessionId, "员工确认问题已解决，会话结束"));
        wsNotifier.notifyAgentsQueue();
        return getSession(sessionId);
    }

    /** 员工直接结束 → CLOSED(未解决但放弃,员工可选项) */
    public ChatSession closeByUser(Long sessionId, String userId) {
        ChatSession session = getOwnedSession(sessionId, userId);
        if (session.getStatus() != SessionStatus.AI_HANDLING) {
            throw new BizException(ErrorCode.PARAM_INVALID, "当前会话状态不支持该操作");
        }
        updateStatus(sessionId, SessionStatus.CLOSED);
        addMessage(sessionId, ChatMessage.SENDER_SYSTEM, null, "员工已结束本次咨询");
        return getSession(sessionId);
    }

    /**
     * 转人工 → WAITING_HUMAN,生成摘要供客服快速了解,并广播提醒客服队列。
     * 摘要 = 首条员工提问(截断),够用且零成本。
     */
    public ChatSession escalate(Long sessionId, String userId) {
        ChatSession session = getOwnedSession(sessionId, userId);
        if (session.getStatus() != SessionStatus.AI_HANDLING) {
            throw new BizException(ErrorCode.PARAM_INVALID, "当前会话已在人工流程中或已结束");
        }
        String summary = buildSummary(sessionId);
        sessionMapper.update(null, new UpdateWrapper<ChatSession>()
                .eq("id", sessionId)
                .set("status", SessionStatus.WAITING_HUMAN.name())
                .set("summary", summary));
        addMessage(sessionId, ChatMessage.SENDER_SYSTEM, null,
                "已转接人工客服，请稍候，客服接入后可直接在此对话");
        wsNotifier.notifyAgentsQueue();   // 提醒在线客服刷新队列
        return getSession(sessionId);
    }

    // ---------------- 客服侧流转 ----------------

    /** 客服队列:全部待接入 + 我处理中的会话 */
    public List<ChatSession> agentQueue(String agentId) {
        QueryWrapper<ChatSession> query = new QueryWrapper<>();
        query.eq("status", SessionStatus.WAITING_HUMAN.name())
                .or(w -> w.eq("status", SessionStatus.HUMAN_HANDLING.name()).eq("agent_id", agentId))
                .orderByAsc("id");
        return sessionMapper.selectList(query);
    }

    /** 客服接入:WAITING_HUMAN → HUMAN_HANDLING;带状态条件的原子更新防两个客服抢单 */
    public ChatSession accept(Long sessionId, String agentId, String agentName) {
        ChatSession session = getSession(sessionId);
        int rows = sessionMapper.update(null, new UpdateWrapper<ChatSession>()
                .eq("id", sessionId)
                .eq("status", SessionStatus.WAITING_HUMAN.name())
                .set("status", SessionStatus.HUMAN_HANDLING.name())
                .set("agent_id", agentId));
        if (rows == 0) {
            throw new BizException(ErrorCode.PARAM_INVALID,
                    session.getStatus() == SessionStatus.HUMAN_HANDLING ? "该会话已被其他客服接入" : "当前会话状态不可接入");
        }
        addMessage(sessionId, ChatMessage.SENDER_SYSTEM, null, "客服 " + agentName + " 已接入，请描述您的问题");
        // 员工在排队页实时等待,立即推送接入通知(前端收到后刷新状态为人工沟通中)
        wsNotifier.sendToSession(sessionId, systemPayload(sessionId, "客服 " + agentName + " 已接入，请描述您的问题"));
        wsNotifier.notifyAgentsQueue();
        return getSession(sessionId);
    }

    /** 客服驳回(重复/无效/已解决) → REJECTED;驳回后员工可重新发起新会话 */
    public ChatSession reject(Long sessionId, String agentId, String reason) {
        ChatSession session = getAgentSession(sessionId, agentId);
        if (reason == null || reason.isBlank()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "驳回原因不能为空");
        }
        sessionMapper.update(null, new UpdateWrapper<ChatSession>()
                .eq("id", sessionId)
                .set("status", SessionStatus.REJECTED.name())
                .set("reject_reason", reason));
        addMessage(sessionId, ChatMessage.SENDER_SYSTEM, null, "客服已关闭本次咨询，原因：" + reason);
        wsNotifier.sendToSession(sessionId, systemPayload(sessionId, "会话已被客服关闭，可重新发起咨询"));
        wsNotifier.notifyAgentsQueue();
        return getSession(sessionId);
    }

    /** 客服确认员工问题已解决 → RESOLVED */
    public ChatSession resolveByAgent(Long sessionId, String agentId) {
        getAgentSession(sessionId, agentId);
        updateStatus(sessionId, SessionStatus.RESOLVED);
        sessionMapper.update(null, new UpdateWrapper<ChatSession>()
                .eq("id", sessionId).set("resolved", 1));
        addMessage(sessionId, ChatMessage.SENDER_SYSTEM, null, "客服确认问题已解决，会话结束");
        wsNotifier.sendToSession(sessionId, systemPayload(sessionId, "客服确认问题已解决，会话结束"));
        wsNotifier.notifyAgentsQueue();
        return getSession(sessionId);
    }

    /**
     * 客服转工单:调用 ticket-service 内部接口建单(creator=发起员工),
     * clientToken = ai-session-{id},重复点击幂等不重复建单。
     */
    public ChatSession toTicket(Long sessionId, String agentId, String category, String priority,
                                String title, String description) {
        ChatSession session = getAgentSession(sessionId, agentId);

        Map<String, Object> request = new HashMap<>();
        request.put("creator_id", session.getUserId());
        request.put("title", (title == null || title.isBlank()) ? truncate(session.getSummary(), 50) : title);
        request.put("category", category);
        request.put("description", (description == null || description.isBlank())
                ? buildTicketDescription(sessionId) : description);
        request.put("priority", priority == null || priority.isBlank() ? "中" : priority);
        request.put("client_token", "ai-session-" + sessionId);

        Result<Map<String, Object>> result = ticketClient.createTicket(request);
        if (result == null || result.getCode() != 0 || result.getData() == null) {
            throw new BizException(ErrorCode.SYSTEM_ERROR,
                    "创建工单失败" + (result == null ? "" : "：" + result.getMsg()));
        }
        String ticketId = String.valueOf(result.getData().get("ticket_id"));

        sessionMapper.update(null, new UpdateWrapper<ChatSession>()
                .eq("id", sessionId)
                .set("status", SessionStatus.TO_TICKET.name())
                .set("ticket_id", ticketId));
        addMessage(sessionId, ChatMessage.SENDER_SYSTEM, null,
                "已生成工单 " + ticketId + "，工程师将尽快处理，可在「我的工单」中查看进度");
        wsNotifier.sendToSession(sessionId, systemPayload(sessionId, "已生成工单 " + ticketId));
        wsNotifier.notifyAgentsQueue();
        return getSession(sessionId);
    }

    // ---------------- 内部工具 ----------------

    /** 客服操作前置校验:必须是本人处理中的会话 */
    private ChatSession getAgentSession(Long sessionId, String agentId) {
        ChatSession session = getSession(sessionId);
        if (session.getStatus() != SessionStatus.HUMAN_HANDLING
                || !agentId.equals(session.getAgentId())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "只能操作本人接入且处理中的会话");
        }
        return session;
    }

    private void updateStatus(Long sessionId, SessionStatus status) {
        sessionMapper.update(null, new UpdateWrapper<ChatSession>()
                .eq("id", sessionId).set("status", status.name()));
    }

    /** 摘要 = 首条员工提问,截断 100 字 */
    private String buildSummary(Long sessionId) {
        QueryWrapper<ChatMessage> query = new QueryWrapper<>();
        query.eq("session_id", sessionId).eq("sender_type", ChatMessage.SENDER_USER)
                .orderByAsc("id").last("LIMIT 1");
        ChatMessage first = messageMapper.selectOne(query);
        return first == null ? "(无提问内容)" : truncate(first.getContent(), 100);
    }

    /** 转工单默认描述:摘要 + 最近 20 条对话记录(截断到 500 字以内,满足工单描述上限) */
    private String buildTicketDescription(Long sessionId) {
        StringBuilder sb = new StringBuilder("【AI 咨询转人工后生成】\n");
        for (ChatMessage m : listMessages(sessionId)) {
            String who = switch (m.getSenderType()) {
                case ChatMessage.SENDER_USER -> "员工";
                case ChatMessage.SENDER_AI -> "AI";
                case ChatMessage.SENDER_AGENT -> "客服";
                default -> "系统";
            };
            sb.append(who).append("：").append(m.getContent()).append('\n');
            if (sb.length() > 450) {
                break;
            }
        }
        return truncate(sb.toString(), 490);
    }

    private Map<String, Object> systemPayload(Long sessionId, String content) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("type", "sys");
        payload.put("session_id", sessionId);
        payload.put("content", content);
        return payload;
    }

    private static String truncate(String text, int max) {
        if (text == null) {
            return "";
        }
        return text.length() <= max ? text : text.substring(0, max);
    }
}
