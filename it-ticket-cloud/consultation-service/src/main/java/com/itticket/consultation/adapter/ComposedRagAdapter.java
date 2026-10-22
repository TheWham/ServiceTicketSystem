package com.itticket.consultation.adapter;
import com.itticket.consultation.adapter.generation.*;
import com.itticket.consultation.adapter.policy.*;
import com.itticket.consultation.adapter.retrieval.*;
import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.enums.*;
import java.math.BigDecimal;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
/** The only answer orchestrator. Providers are selected in Spring assembly, never here. */
public final class ComposedRagAdapter implements RagAdapter {
    private static final Logger log = LoggerFactory.getLogger(ComposedRagAdapter.class);
    private final RequestClassifier classifier;
    private final KnowledgeRetriever retriever;
    private final RetrievalPolicy policy;
    private final AnswerGenerator generator;
    /** 仅当 Function Calling 开启时为 true —— agent 关了就不消费判定结果里的 tool。 */
    private final boolean toolBypassEnabled;
    public ComposedRagAdapter(RequestClassifier classifier, KnowledgeRetriever retriever,
                              RetrievalPolicy policy, AnswerGenerator generator, boolean toolBypassEnabled) {
        this.classifier = classifier; this.retriever = retriever; this.policy = policy; this.generator = generator;
        this.toolBypassEnabled = toolBypassEnabled;
    }
    @Override public RagResult answer(RagQuery query, RagCallContext context) {
        List<String> retrieved = List.of();
        try {
            // 一次判定给全「走哪条路」与「要不要调工具」；拒答/澄清的门禁仍最靠前，不被工具意图越过
            RequestVerdict verdict = classifier.classify(query, context);
            log.info("[判定] domain={} tool={} requestId={}", verdict.domain(), verdict.tool(), context.requestId());
            RagResult domainVerdict = restrict(verdict.domain());
            if (domainVerdict != null) return domainVerdict;
            RetrievalResult result = retriever.retrieve(query, context);
            retrieved = result.items().stream().map(RetrievedKnowledge::versionId).distinct().toList();
            context.audit().recordRetrievedVersions(retrieved);
            // 检索侧的 domain 是关键词粗判，实测会误伤（「我上周报的」含子串「周报」→ OFF_TOPIC）。
            // 语义判定是主判且已放行到这里的必为 OFFICE_IT，故关键词粗判只在 HIGH_RISK 红线上
            // 保留否决权（语义说能走、检索说高危时，宁可拦下）；OFF_TOPIC/UNCERTAIN 不得反悔。
            if (result.domain() == OfficeDomain.HIGH_RISK) {
                RagResult blocked = restrict(OfficeDomain.HIGH_RISK);
                if (blocked != null) return blocked;
            }
            // 工具意图（查工单/建单）：预检索无果时不直接拒答，放行给 agent 用工具去查。
            boolean toolBypass = toolBypassEnabled && !RequestVerdict.NO_TOOL.equals(verdict.tool());
            if (result.refusalReason() != null && !toolBypass)
                return RagResult.refuse(result.refusalReason(), null, retrieved);
            List<RetrievedKnowledge> material = policy.material(result, context);
            if (result.reliable() && material.isEmpty() && !toolBypass)
                return RagResult.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, null, retrieved);
            context.timeoutMillis(Long.MAX_VALUE);
            GenerationResult generated = generator.generate(query, material, context);
            context.timeoutMillis(Long.MAX_VALUE);
            Map<String, RetrievedKnowledge> byVersion = new LinkedHashMap<>();
            material.forEach(item -> byVersion.put(item.versionId(), item));
            if (generated.usedVersionIds().stream().anyMatch(id -> !byVersion.containsKey(id)))
                throw DependencyFailure.invalid();
            if (generated.refusalReason() != null)
                return RagResult.refuse(generated.refusalReason(), generated.modelVersion(), retrieved);
            // 「有材料却零引用=伪造嫌疑」守卫：但工具意图放行的作答实据来自工具返回
            // （工单列表/建单草稿），本就不依赖知识引用——检索给建单类请求带出的低分杂项
            // （如「员工IT故障自助排查流程」0.44）不构成引用义务，零引用是合法状态。
            if (generated.replyType() == AiReplyType.REFUSE
                    || !material.isEmpty() && generated.usedVersionIds().isEmpty() && !toolBypass)
                return RagResult.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, generated.modelVersion(), retrieved);
            List<KnowledgeCitationDto> citations = generated.usedVersionIds().stream().distinct()
                    .map(byVersion::get).map(item -> new KnowledgeCitationDto(item.articleId(), item.versionId(),
                            item.title(), item.score(), item.snippet())).toList();
            // 工具意图的作答实据来自工具返回（工单列表/建单草稿），不来自知识引用——
            // 即使检索带出了材料也按「无知识依据」通道放行（AiAnswerGuard 第 7 条），
            // 否则会被第 8 条「知识回答必须带引用」当伪造拒掉。置信度门槛照常约束。
            boolean general = material.isEmpty() || (toolBypass && generated.usedVersionIds().isEmpty());
            String text = generated.answerText();
            // 工具意图越过的作答是「凭工具查到的实据」（如本人工单列表），不是通用建议——
            // 加这句前缀会与正文自相矛盾。general 标记本身保留（确实无知识库引用），只是不展示该措辞。
            if (general && !toolBypass && text != null && !text.isBlank())
                text = "以下为通用办公 IT 建议，无知识库依据。\n\n" + text;
            if (text != null && text.length() > 12000) throw DependencyFailure.invalid();
            RagResult answered = new RagResult(RagStatus.SUCCESS, generated.replyType(), text, citations,
                    generated.confidence(), null, generated.modelVersion(), retrieved, 0, null, general, false);
            // 人机回环:AI 只产建单草稿(不落库),随结果返回员工确认后才建单
            return generated.ticketDraft() == null ? answered : answered.withTicketDraft(generated.ticketDraft());
        } catch (RetrievalPolicy.StaleKnowledge stale) {
            return RagResult.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, null, retrieved);
        } catch (DependencyFailure failure) {
            return failure.result(retrieved);
        }
    }
    private static RagResult restrict(OfficeDomain domain) {
        return switch (domain) {
            case OFFICE_IT -> null;
            case OFF_TOPIC -> RagResult.refuse(AiRefusalReason.OFF_TOPIC, null, List.of());
            case HIGH_RISK -> RagResult.refuse(AiRefusalReason.HIGH_RISK_TOPIC, null, List.of());
            case UNCERTAIN -> new RagResult(RagStatus.SUCCESS, AiReplyType.CLARIFY,
                    "请补充遇到问题的办公设备或应用、具体表现及错误提示。",
                    List.of(), BigDecimal.ONE, null, null, List.of(), 0, null, false, false);
        };
    }
}
