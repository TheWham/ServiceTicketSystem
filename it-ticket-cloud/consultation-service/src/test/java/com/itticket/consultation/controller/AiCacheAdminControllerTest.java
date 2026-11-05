package com.itticket.consultation.controller;

import com.itticket.consultation.adapter.RagStatus;
import com.itticket.consultation.adapter.RagQuery;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagExecutionAudit;
import com.itticket.consultation.adapter.RagResult;
import com.itticket.consultation.adapter.RagCaller;
import com.itticket.consultation.adapter.cache.SemanticAnswerCache;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiEnvelope;
import com.itticket.consultation.api.ApiException;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.service.AuthzService;
import com.itticket.consultation.service.CurrentUser;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.math.BigDecimal;
import java.time.Clock;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

/**
 * 缓存指标导出端点的门禁与载荷测试(不启动 Spring,直接 new + Mockito)。
 * 授权规则本身(AiCacheAdminControllerTest):管理员放行、员工 FORBIDDEN。
 */
class AiCacheAdminControllerTest {

    private static CurrentUser platformAdmin() {
        return new CurrentUser("U_ADMIN", com.itticket.consultation.enums.RoleCode.PLATFORM_ADMIN, null);
    }

    private static CurrentUser employee() {
        return new CurrentUser("U_EMP", com.itticket.consultation.enums.RoleCode.EMPLOYEE, null);
    }

    /** 假嵌入客户端:按 AtomicReference 中的当前向量回答,便于写/查各问之间切换向量。 */
    private static com.itticket.consultation.adapter.embedding.EmbeddingClient fakeEmbeds(
            AtomicReference<float[]> vectors) {
        return (text, context) -> vectors.get();
    }

    private static SemanticAnswerCache cacheWithOneHitAndOneMiss(
            AtomicReference<float[]> vectors) {
        ConsultationProperties.Ai.Cache config = new ConsultationProperties.Ai.Cache();
        config.setEnabled(true);
        config.setThreshold(0.93);
        config.setEmbeddingModel("bge-m3");
        SemanticAnswerCache cache = new SemanticAnswerCache(
                config, fakeEmbeds(vectors), (articleId, versionId) -> true, Clock.systemDefaultZone());

        RagQuery first = new RagQuery("S1", "VPN 断连怎么办", "C_NET", "ASSET1", 5,
                new RagCaller("U_EMP01", "EMPLOYEE"));
        RagQuery miss = new RagQuery("S2", "报表不能用看什么模块", "C_SW", "ASSET2", 5,
                new RagCaller("U_EMP02", "EMPLOYEE"));
        RagCallContext context = new RagCallContext("req-stat", System.nanoTime() + 10_000_000_000L,
                new RagExecutionAudit());

        vectors.set(new float[]{1f, 0f});
        cache.write(first, context, answered());
        assertThat(cache.lookup(first, context)).isPresent(); // 命中一次
        vectors.set(new float[]{0f, 1f});
        assertThat(cache.lookup(miss, context)).isEmpty(); // 真实未命中一次
        return cache;
    }

    private static RagResult answered() {
        return new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, "重启路由器并检查网线。",
                List.of(new KnowledgeCitationDto("A1", "V1", "VPN 排障", new BigDecimal("0.90"), "摘要")),
                new BigDecimal("0.80"), null, "deepseek-v4-flash", List.of("V1"), 10, null, false, false);
    }


    @Test
    void requirePlatformAdminPureCheck() {
        AuthzService authz = new AuthzService(new ConsultationProperties());

        assertThatThrownBy(() -> authz.requirePlatformAdmin(employee()))
                .isInstanceOf(ApiException.class)
                .satisfies(e -> assertThat(((ApiException) e).getCode()).isEqualTo(ApiCode.FORBIDDEN));
        assertThatThrownBy(() -> authz.requirePlatformAdmin(null))
                .isInstanceOf(ApiException.class);
        // 平台管理员放行(不抛即通过)
        authz.requirePlatformAdmin(platformAdmin());
    }

    @Test
    void adminExportsOperationalCounters() {
        AtomicReference<float[]> vectors = new AtomicReference<>();
        SemanticAnswerCache cache = cacheWithOneHitAndOneMiss(vectors);
        AuthzService authz = mock(AuthzService.class);
        when(authz.currentUser()).thenReturn(platformAdmin());
        AiCacheAdminController controller = new AiCacheAdminController(authz, cache);

        ApiEnvelope<com.itticket.consultation.adapter.cache.CacheStats> envelope = controller.export();

        assertThat(envelope.code()).isEqualTo(ApiCode.SUCCESS.name());
        assertThat(envelope.data().hits()).isEqualTo(1L);
        assertThat(envelope.data().realMisses()).isEqualTo(1L);
        assertThat(envelope.data().hitRate()).isEqualTo(0.5);
        ArgumentCaptor<CurrentUser> principal = ArgumentCaptor.forClass(CurrentUser.class);
        verify(authz).requirePlatformAdmin(principal.capture());
        assertThat(principal.getValue().isPlatformAdmin()).isTrue();
    }

    @Test
    void forbiddenPropagatesAsApiException() {
        AtomicReference<float[]> vectors = new AtomicReference<>();
        SemanticAnswerCache cache = cacheWithOneHitAndOneMiss(vectors);
        AuthzService authz = mock(AuthzService.class);
        when(authz.currentUser()).thenReturn(employee());
        doThrow(new ApiException(ApiCode.FORBIDDEN, "仅平台管理员可查看缓存指标"))
                .when(authz).requirePlatformAdmin(any());
        AiCacheAdminController controller = new AiCacheAdminController(authz, cache);

        assertThatThrownBy(controller::export)
                .isInstanceOf(ApiException.class)
                .satisfies(e -> assertThat(((ApiException) e).getCode()).isEqualTo(ApiCode.FORBIDDEN));
    }

    @Test
    void disabledCacheStillExportsZeroCounters() {
        AuthzService authz = mock(AuthzService.class);
        when(authz.currentUser()).thenReturn(platformAdmin());
        AiCacheAdminController controller = new AiCacheAdminController(authz, SemanticAnswerCache.disabled());

        ApiEnvelope<com.itticket.consultation.adapter.cache.CacheStats> envelope = controller.export();

        assertThat(envelope.data().hits()).isZero();
        assertThat(envelope.data().entries()).isZero();
        assertThat(envelope.data().hitRate()).isZero();
        verify(authz).requirePlatformAdmin(any());
    }
}
