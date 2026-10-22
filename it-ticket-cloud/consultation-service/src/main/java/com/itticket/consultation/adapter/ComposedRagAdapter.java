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
/**
 * AI 回答的唯一编排器 —— 一次员工消息在这里走完全部七步
 * （全景图见 adapter.policy 包的 package-info，第 ① 环的判定器也在那个包）：
 *
 * <ol>
 *   <li><b>① 意图判定</b>：classifier.classify 一次给出 domain（拒答空间）+ tool（工具意图）；</li>
 *   <li><b>② 领域门禁</b>：OFF_TOPIC/HIGH_RISK 短路拒答、UNCERTAIN 追问——位置最靠前，
 *       工具意图永远顶不开它；检索侧的域粗判只保留 HIGH_RISK 否决权（见下方注释）；</li>
 *   <li><b>③ 知识检索</b>：retriever → rag-service(:8302) → Python 检索服务(:8310)，
 *       返回材料 + reliable/reason；</li>
 *   <li><b>④ 工具意图放行</b>：检索无果/低置信本应拒答；若判定给了具体工具且 agent 已开启
 *       （构造参数 toolBypassEnabled = pythonAgentClient.enabled()），放行给第 ⑤ 步——
 *       这是 Function Calling 智能体（查工单/建单）唯一的入口；</li>
 *   <li><b>⑤ 生成</b>：generator 在装配期二选一——tool 路径走 PythonAgentClient(:8320，
 *       ReAct 循环 + 白名单工具)，知识路径走 OpenAiCompatibleModelClient（单轮、引用 material）；</li>
 *   <li><b>⑥ 引用守卫（本类内）+ 输出守卫（AiAnswerGuard，service 层）</b>：
 *       usedVersionIds ⊆ 预检索材料、PUBLISHED 复核、置信度门槛；
 *       工具意图作答实据来自工具返回，标记 generalAnswer=true 走「无知识依据」通道；</li>
 *   <li><b>⑦ 返回</b>：正常回答带引用；建单请求额外携带带外 ticketDraft（人机回环——
 *       员工确认后才真正建单，落库在 ConsultationService.confirmTicketDraft）。</li>
 * </ol>
 *
 * <p>失败语义：检索/生成的一切依赖故障都收敛为 RagResult.failure（AiAnswerGuard 统一转
 * 结构化拒答），不让异常裸抛出本类——「主链路不可阻断」（RD-013）。
 */
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
