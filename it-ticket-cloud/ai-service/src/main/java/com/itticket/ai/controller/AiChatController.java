package com.itticket.ai.controller;

import com.itticket.ai.dto.ChatRequest;
import com.itticket.ai.entity.ChatMessage;
import com.itticket.ai.entity.ChatSession;
import com.itticket.ai.service.AiChatService;
import com.itticket.ai.service.ChatSessionService;
import com.itticket.ai.service.KnowledgeService;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 员工侧 AI 咨询接口。
 * 典型流程:POST /chat(可多次) → 满意则 POST /sessions/{id}/resolve 结束;
 *          不满意 → POST /sessions/{id}/escalate 转人工 或 POST /sessions/{id}/close 直接结束。
 */
@RestController
@RequestMapping("/api/v1/ai")
@RequiredArgsConstructor
public class AiChatController {

    private final AiChatService aiChatService;
    private final ChatSessionService sessionService;

    /** 提问(AI 解答);session_id 为空自动开新会话 */
    @PostMapping("/chat")
    public Result<Map<String, Object>> chat(@RequestBody ChatRequest request) {
        if (request.getQuestion() == null || request.getQuestion().trim().length() < 2) {
            throw new BizException(ErrorCode.PARAM_INVALID, "问题至少 2 个字符");
        }
        if (request.getQuestion().trim().length() > 500) {
            throw new BizException(ErrorCode.PARAM_INVALID, "问题不能超过 500 个字符");
        }
        UserContext.CurrentUser user = UserContext.get();
        AiChatService.ChatOutcome outcome = aiChatService.chat(
                user.getUserId(), request.getSessionId(), request.getQuestion().trim());

        // 命中的知识来源一并返回,前端可展示"参考了哪些资料"
        List<Map<String, Object>> sources = outcome.sources().stream()
                .map(hit -> {
                    Map<String, Object> source = new HashMap<String, Object>();
                    source.put("id", hit.knowledge().getId());
                    source.put("title", hit.knowledge().getTitle());
                    source.put("category", hit.knowledge().getCategory());
                    return source;
                })
                .toList();
        Map<String, Object> data = new HashMap<>();
        data.put("session_id", outcome.session().getId());
        data.put("answer", outcome.answer());
        data.put("status", outcome.session().getStatus().name());
        data.put("sources", sources);
        return Result.ok(data);
    }

    /** 反馈已解决 → 会话结束,不生成工单 */
    @PostMapping("/sessions/{id}/resolve")
    public Result<ChatSession> resolve(@PathVariable Long id) {
        return Result.ok("已确认解决，感谢反馈",
                sessionService.resolveByUser(id, UserContext.get().getUserId()));
    }

    /** 转人工客服 → 进入待接入队列 */
    @PostMapping("/sessions/{id}/escalate")
    public Result<ChatSession> escalate(@PathVariable Long id) {
        return Result.ok("已转接人工客服，请稍候",
                sessionService.escalate(id, UserContext.get().getUserId()));
    }

    /** 员工直接结束(员工可选项:转人工 或 直接结束) */
    @PostMapping("/sessions/{id}/close")
    public Result<ChatSession> close(@PathVariable Long id) {
        return Result.ok("已结束本次咨询",
                sessionService.closeByUser(id, UserContext.get().getUserId()));
    }

    /** 我的会话列表(最近 20 条) */
    @GetMapping("/sessions/mine")
    public Result<List<ChatSession>> mySessions() {
        return Result.ok(sessionService.mySessions(UserContext.get().getUserId()));
    }

    /** 会话消息记录(本人会话) */
    @GetMapping("/sessions/{id}/messages")
    public Result<List<ChatMessage>> messages(@PathVariable Long id) {
        sessionService.getOwnedSession(id, UserContext.get().getUserId());
        return Result.ok(sessionService.listMessages(id));
    }
}
