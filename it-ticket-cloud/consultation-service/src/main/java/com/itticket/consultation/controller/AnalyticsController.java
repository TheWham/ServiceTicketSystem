package com.itticket.consultation.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.itticket.consultation.adapter.DependencyFailure;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagExecutionAudit;
import com.itticket.consultation.adapter.RagStatus;
import com.itticket.consultation.adapter.analytics.AnalyticsClient;
import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiEnvelope;
import com.itticket.consultation.api.ApiException;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.dto.AnalyticsQueryRequest;
import com.itticket.consultation.enums.RoleCode;
import com.itticket.consultation.service.AuthzService;
import com.itticket.consultation.service.CurrentUser;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.concurrent.TimeUnit;

/**
 * 跨工单分析接口（员工侧智能客服的「跨记录宏观归纳」入口）。
 *
 * <p><b>为什么单独开一个接口，而不是只走问答链路</b>：问答链路
 * （{@code ComposedRagAdapter}）的回包结构是「一段正文 + 引用」，装不下统计明细。
 * 而分析结果的价值一半在**明细**上 —— 前端要渲染分布表格、要能下钻到源单号。
 * 所以这里原样透传 Python 的完整负载（含 {@code analyticsFacts}），
 * 让前端读 facts 而不是去解析模型写的正文：模型编造一个假的 42% 在结构上就不可能。
 *
 * <p><b>两条路径共用同一个后端口径</b>：问答链路的 {@code AnalyticsClient.analyze}
 * 与这里的 {@code queryPayload} 调的是同一个 Python 接口、同一份 facts。
 *
 * <p><b>与客服入口的关键差别</b>：本入口**不预设 upstreamIntent**。客服入口由 Java
 * 分类器先定性、判为分析型才进来；而本入口是工程师主动进统计工作台，他也可能问一个
 * 具体故障 —— 那种问题必须由 Python 判为非分析型后**熔断拒答**（reason=
 * {@code OUT_OF_SCOPE}）并引导去智能客服，而不是硬给一份工单分布统计。
 *
 * <p><b>权限</b>：跨工单聚合是跨人分析，<b>仅 ENGINEER 可调</b>，
 * 与 ticket-service 侧 {@code ANALYTICS_ROLES}、Python 侧 {@code ALLOWED_ROLES} 对齐。
 * 这里这道是权威的一道。
 */
@Validated
@RestController
@RequestMapping("/api/v1/analytics")
@RequiredArgsConstructor
public class AnalyticsController {

    private final AnalyticsClient analyticsClient;
    private final AuthzService authzService;

    /** 跑一次跨工单分析，返回结论 + 统计明细（analyticsFacts）+ 链路追踪。 */
    @PostMapping("/query")
    public ApiEnvelope<JsonNode> query(@Valid @RequestBody AnalyticsQueryRequest request) {
        CurrentUser user = authzService.currentUser();   // 触发认证校验：未认证不得调用
        if (user.role() != RoleCode.ENGINEER) {
            throw new ApiException(ApiCode.FORBIDDEN, "跨工单统计分析仅限工程师权限");
        }
        if (!analyticsClient.enabled()) {
            throw new ApiException(ApiCode.AI_UNAVAILABLE, "分析链路未启用（itticket.consultation.ai.analytics）");
        }
        // 与 confirmTicketDraft 同款：独立调用预算，不复用上游残留的 deadline。
        // 240s 是给归因模型留的余量：本端点模型是推理型，一次分析实测 43~95 秒，
        // 预算必须比 AnalyticsClient 的 180s 更宽，否则会先被 deadline 掐掉。
        RagCallContext call = new RagCallContext(RequestContext.get(),
                System.nanoTime() + TimeUnit.SECONDS.toNanos(240),
                new RagExecutionAudit());
        try {
            return ApiEnvelope.ok(analyticsClient.queryPayload(request.question(),
                    user.userId(), user.role().getValue(), call,
                    // 空串＝不预设意图：让 Python 判定，判非分析型即熔断
                    ""), RequestContext.get());
        } catch (DependencyFailure failure) {
            // 依赖失败如实透出，不用"通用建议"顶上（AGENTS.md：不静默回退）
            throw new ApiException(ApiCode.AI_UNAVAILABLE,
                    failure.status() == RagStatus.TIMEOUT ? "分析链路超时" : "分析链路暂不可用");
        }
    }
}