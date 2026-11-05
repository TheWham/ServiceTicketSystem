package com.itticket.consultation.controller;

import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiException;
import com.itticket.consultation.dto.AiChatRequest;
import com.itticket.consultation.service.AiConsultationService;
import com.itticket.consultation.service.AuthzService;
import com.itticket.consultation.service.ConsultationService;
import com.itticket.consultation.service.CurrentUser;
import com.itticket.consultation.service.stream.AiChatStreamOrchestrator;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyEmitter;

import java.lang.reflect.Field;
import java.util.function.Consumer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * /stream 端点装配线(T-6):控制器只做鉴权→桥接→登记断连回调三件事,
 * 一切时序/事件语义由编排器测试锁定(见 AiChatStreamOrchestratorTest)。
 */
class AiChatStreamControllerTest {

    private static CurrentUser employee() {
        return new CurrentUser("U_EMP01", com.itticket.consultation.enums.RoleCode.EMPLOYEE, null);
    }

    private static AiChatRequest request(String message) {
        return new AiChatRequest(message, null);
    }

    private static Object callback(ResponseBodyEmitter emitter, String field) throws Exception {
        Field declared = ResponseBodyEmitter.class.getDeclaredField(field);
        declared.setAccessible(true);
        return declared.get(emitter);
    }

    @Test
    void unauthenticatedRequestIsRejectedBeforeAnyOrchestratorWork() {
        AuthzService authz = mock(AuthzService.class);
        when(authz.currentUser()).thenThrow(new ApiException(ApiCode.UNAUTHENTICATED, "未登录"));
        AiChatStreamOrchestrator orchestrator = mock(AiChatStreamOrchestrator.class);
        AiConsultationController controller = new AiConsultationController(
                mock(AiConsultationService.class), mock(ConsultationService.class), authz, orchestrator);

        assertThatThrownBy(() -> controller.chatStream("C-1", "key-1", request("投影仪没有信号")))
                .isInstanceOf(ApiException.class)
                .satisfies(e -> assertThat(((ApiException) e).getCode()).isEqualTo(ApiCode.UNAUTHENTICATED));
        verify(orchestrator, never()).openStream(any(), any(), any(), any(), any());
    }

    @Test
    void wiresOrchestratorWithCallerIdentityAndRegistersAllDisconnectCallbacks() throws Exception {
        AuthzService authz = mock(AuthzService.class);
        when(authz.currentUser()).thenReturn(employee());
        AiChatStreamOrchestrator orchestrator = mock(AiChatStreamOrchestrator.class);
        AiChatStreamOrchestrator.SseHandle handle = mock(AiChatStreamOrchestrator.SseHandle.class);
        when(orchestrator.openStream(any(), any(), any(), any(), any())).thenReturn(handle);
        AiConsultationController controller = new AiConsultationController(
                mock(AiConsultationService.class), mock(ConsultationService.class), authz, orchestrator);

        ResponseBodyEmitter emitter =
                controller.chatStream("C-1", "key-1", request("投影仪没有信号"));

        assertThat(emitter).isNotNull();
        ArgumentCaptor<AiChatStreamOrchestrator.EventSink> sink =
                ArgumentCaptor.forClass(AiChatStreamOrchestrator.EventSink.class);
        verify(orchestrator).openStream(org.mockito.ArgumentMatchers.eq(employee()),
                org.mockito.ArgumentMatchers.eq("C-1"),
                org.mockito.ArgumentMatchers.eq(request("投影仪没有信号")),
                org.mockito.ArgumentMatchers.eq("key-1"), sink.capture());
        assertThat(sink.getValue()).isInstanceOf(SseChatEventSink.class);

        // 断连回调三挂:超时/错误/正常完成都应让编排器本流腾位(漏挂会卡死会话队列)。
        ((Runnable) callback(emitter, "timeoutCallback")).run();
        verify(handle).close();
        ((Consumer<Throwable>) callback(emitter, "errorCallback")).accept(new IllegalStateException("断开"));
        verify(handle, org.mockito.Mockito.times(2)).close();
        ((Runnable) callback(emitter, "completionCallback")).run();
        verify(handle, org.mockito.Mockito.times(3)).close();
    }
}
