package com.itticket.ai.service;

import com.itticket.ai.entity.ChatMessage;
import com.itticket.ai.entity.ChatSession;
import com.itticket.ai.enums.SessionStatus;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * AI 问答编排:消息落库 → 知识库检索(RAG) → 拼 Prompt → 调大模型 → 回复落库。
 * 两级降级:embedding 未配置 → 跳过检索(通用回答);chat 未配置 → 固定提示语。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AiChatService {

    /** 问答结果 */
    public record ChatOutcome(ChatSession session, String answer, List<KnowledgeService.Hit> sources) {
    }

    private final ChatSessionService sessionService;
    private final KnowledgeService knowledgeService;
    private final LlmClient llmClient;

    /**
     * 员工提问。
     * @param sessionId 为空则新建会话;非空时校验归属且状态必须是 AI_HANDLING
     */
    public ChatOutcome chat(String userId, Long sessionId, String question) {
        // 1. 会话准备与状态校验
        ChatSession session = (sessionId == null)
                ? sessionService.createSession(userId)
                : sessionService.getOwnedSession(sessionId, userId);
        if (session.getStatus() == SessionStatus.WAITING_HUMAN
                || session.getStatus() == SessionStatus.HUMAN_HANDLING) {
            throw new BizException(ErrorCode.PARAM_INVALID, "当前会话已转人工，请在聊天窗口中与客服沟通");
        }
        if (session.getStatus() != SessionStatus.AI_HANDLING) {
            throw new BizException(ErrorCode.PARAM_INVALID, "该会话已结束，请重新发起咨询");
        }

        // 2. 员工消息落库
        sessionService.addMessage(session.getId(), ChatMessage.SENDER_USER, userId, question);

        // 3. 大模型未配置 → 降级提示(流程仍可走通:转人工/直接结束不受影响)
        if (!llmClient.isEnabled()) {
            String fallback = "AI 服务暂未配置大模型密钥，无法智能作答。\n"+
                    "您可以点击「转人工」由客服协助处理，或直接提交 IT 工单。";
            sessionService.addMessage(session.getId(), ChatMessage.SENDER_AI, null, fallback);
            return new ChatOutcome(session, fallback, List.of());
        }

        // 4. RAG 检索(embedding 未配置时返回空,自动降级为通用回答)
        List<KnowledgeService.Hit> hits = knowledgeService.search(question);

        // 5. 拼 Prompt 并调用大模型
        String answer = llmClient.chat(buildSystemPrompt(hits), question);

        // 6. AI 回复落库并返回
        sessionService.addMessage(session.getId(), ChatMessage.SENDER_AI, null, answer);
        return new ChatOutcome(session, answer, hits);
    }

    /**
     * 系统 Prompt:角色设定 + 防幻觉约束 + 参考资料。
     * 有资料 → 严格基于资料回答;无资料 → 通用建议并明确标注,引导转人工。
     */
    private String buildSystemPrompt(List<KnowledgeService.Hit> hits) {
        StringBuilder prompt = new StringBuilder();
        prompt.append("你是公司内部的 IT 支持助手，帮助员工解决办公 IT 问题。\n");
        prompt.append("回答要求：\n");
        prompt.append("1. 分步骤回答，每步一句话，语言通俗，避免专业黑话；\n");
        prompt.append("2. 不要编造公司内部系统的具体操作路径；\n");

        if (hits.isEmpty()) {
            prompt.append("3. 本次知识库未检索到相关资料，请基于通用 IT 知识给出排查建议，"+
                    "开头必须注明「知识库暂未覆盖该问题，以下为通用建议」，" +
                    "结尾提示员工可点击「转人工」获得客服帮助。\n");
        } else {
            prompt.append("3. 优先依据下面【参考资料】回答；资料不足以完全解决时，"+
                    "可补充通用建议并提示可「转人工」；\n");
            prompt.append("4. 回答末尾用 [资料1] [资料2] 形式标注实际引用的资料编号，未引用则不标注。\n\n");
            prompt.append("【参考资料】\n");
            for (int i = 0; i < hits.size(); i++) {
                KnowledgeService.Hit hit = hits.get(i);
                prompt.append("[资料").append(i + 1).append("] 分类：")
                        .append(hit.knowledge().getCategory() == null ? "通用" : hit.knowledge().getCategory())
                        .append(" | ").append(hit.knowledge().getContent())
                        .append("\n");
            }
        }
        return prompt.toString();
    }
}
