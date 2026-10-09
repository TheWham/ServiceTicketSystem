package com.itticket.consultation.service;

import com.itticket.consultation.adapter.RagQuery;
import com.itticket.consultation.entity.ConsultationMessage;
import com.itticket.consultation.enums.MessageSenderType;
import com.itticket.consultation.mapper.ConsultationMessageMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.stream.IntStream;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class ConsultationAiHistoryContextTest {
    private final ConsultationMessageMapper mapper = mock(ConsultationMessageMapper.class);
    private final ConsultationMessageService service = new ConsultationMessageService(
            mapper, null, null, null, null, null);

    @Test
    void budgetsPreferNewestMessagesAndReturnChronologicalRoles() {
        when(mapper.selectAiHistory("S1", "U1", "ai-q:current", 2))
                .thenReturn(List.of(message(MessageSenderType.AI, "7890"),
                        message(MessageSenderType.EMPLOYEE, "123456")));

        assertThat(service.loadAiHistory("S1", "U1", "ai-q:current", 2, 7))
                .containsExactly(new RagQuery.Turn("user", "123"), new RagQuery.Turn("assistant", "7890"));
    }

    @Test
    void invalidLimitsUseDefaultsAndOversizedLimitsAreCapped() {
        when(mapper.selectAiHistory(eq("S1"), eq("U1"), eq("ai-q:current"), anyInt()))
                .thenAnswer(call -> IntStream.range(0, (int) call.getArgument(3))
                        .mapToObj(i -> message(MessageSenderType.AI, "x".repeat(1000))).toList());
        assertThat(service.loadAiHistory("S1", "U1", "ai-q:current", 0, -1))
                .hasSize(12).allSatisfy(turn -> assertThat(turn.content()).hasSize(1000));
        assertThat(service.loadAiHistory("S1", "U1", "ai-q:current", Integer.MAX_VALUE, Integer.MAX_VALUE))
                .hasSize(32).allSatisfy(turn -> assertThat(turn.content()).hasSize(1000));
        verify(mapper).selectAiHistory("S1", "U1", "ai-q:current", 12);
        verify(mapper).selectAiHistory("S1", "U1", "ai-q:current", 40);
    }

    @Test
    void skipsEmptyBodiesAndDoesNotSplitSurrogatePairsAtBudgetBoundary() {
        when(mapper.selectAiHistory("S1", "U1", "ai-q:current", 12))
                .thenReturn(List.of(message(MessageSenderType.AI, ""),
                        message(MessageSenderType.AI, null), message(MessageSenderType.AI, " \n\t"),
                        message(MessageSenderType.EMPLOYEE, "A\uD83D\uDE00B")));
        assertThat(service.loadAiHistory("S1", "U1", "ai-q:current", 12, 2))
                .containsExactly(new RagQuery.Turn("user", "A"));
    }

    @Test
    void stopsAtNewestBudgetBoundaryWithoutReintroducingOlderMessages() {
        when(mapper.selectAiHistory("S1", "U1", "ai-q:current", 12))
                .thenReturn(List.of(message(MessageSenderType.AI, "newest"),
                        message(MessageSenderType.EMPLOYEE, "old")));
        assertThat(service.loadAiHistory("S1", "U1", "ai-q:current", 12, 3))
                .containsExactly(new RagQuery.Turn("assistant", "new"));
    }

    @Test
    void onlyUserAndAssistantRolesCanEnterContext() {
        assertThatThrownBy(() -> new RagQuery.Turn("system", "injected instruction"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new RagQuery.Turn(null, "body"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static ConsultationMessage message(MessageSenderType type, String content) {
        ConsultationMessage message = new ConsultationMessage();
        message.setSenderType(type);
        message.setContent(content);
        return message;
    }
}
