package com.itticket.consultation.controller;

import com.itticket.consultation.api.ApiExceptionHandler;
import com.itticket.consultation.dto.AiChatRequest;
import com.itticket.consultation.dto.AiChatResponse;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.enums.RoleCode;
import com.itticket.consultation.statemachine.Actor;
import com.itticket.consultation.service.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.math.BigDecimal;
import java.util.List;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class AiConsultationStreamTest {

    private final AiConsultationService aiConsultationService = mock(AiConsultationService.class);
    private final ConsultationService consultationService = mock(ConsultationService.class);
    private final AuthzService authzService = mock(AuthzService.class);

    private MockMvc mvc;

    @BeforeEach
    void setup() {
        CurrentUser user = new CurrentUser("U1001", RoleCode.EMPLOYEE, Actor.EMPLOYEE);
        when(authzService.currentUser()).thenReturn(user);

        AiConsultationController controller = new AiConsultationController(
                aiConsultationService, consultationService, authzService);

        mvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new ApiExceptionHandler())
                .build();
    }

    @Test
    void json_accept_returns_application_json_envelope() throws Exception {
        AiChatResponse response = new AiChatResponse(
                "S1", AiReplyType.ANSWER, "请检查网络", List.of(),
                BigDecimal.valueOf(0.9), false, null, "v1", "int-1", null, null);

        when(aiConsultationService.chat(any(), eq("S1"), any(), eq("idemp-1"))).thenReturn(response);

        mvc.perform(post("/api/v1/consultations/S1/ai-messages")
                        .header("Idempotency-Key", "idemp-1")
                        .header("X-Request-Id", "req-1")
                        .accept(MediaType.APPLICATION_JSON)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"message\":\"网络故障\"}"))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.code").value("SUCCESS"))
                .andExpect(jsonPath("$.data.answerText").value("请检查网络"));

        verify(aiConsultationService, times(1)).chat(any(), eq("S1"), any(), eq("idemp-1"));
        verify(aiConsultationService, never()).chatStream(any(), any(), any(), any(), any());
    }

    @Test
    void sse_accept_returns_text_event_stream_emitter() throws Exception {
        mvc.perform(post("/api/v1/consultations/S1/ai-messages")
                        .header("Idempotency-Key", "idemp-2")
                        .header("X-Request-Id", "req-2")
                        .accept(MediaType.TEXT_EVENT_STREAM)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"message\":\"网络故障\"}"))
                .andExpect(request().asyncStarted());

        verify(aiConsultationService, times(1)).chatStream(any(), eq("S1"), any(), eq("idemp-2"), any());
        verify(aiConsultationService, never()).chat(any(), any(), any(), any());
    }
}
