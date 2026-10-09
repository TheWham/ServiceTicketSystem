package com.itticket.consultation.service;

import com.itticket.consultation.adapter.RagQuery;
import com.itticket.consultation.mapper.ConsultationMessageMapper;
import org.apache.ibatis.session.Configuration;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;
import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/** Runs the production mapper against an isolated H2 database in MySQL mode. */
class ConsultationAiHistoryDatabaseContextTest {
    @Test
    void persistedHistoryFiltersBeforeLimitingAndUsesStableChronologicalOrder() throws Exception {
        try (Connection connection = DriverManager.getConnection("jdbc:h2:mem:" + UUID.randomUUID() + ";MODE=MySQL")) {
            try (var sql = connection.createStatement()) {
                sql.execute("CREATE TABLE consultation_message (message_id VARCHAR(64), session_id VARCHAR(64), "
                        + "sender_id VARCHAR(64), sender_type VARCHAR(32), client_message_id VARCHAR(64), "
                        + "content TEXT, sent_at TIMESTAMP, withdrawn_at TIMESTAMP)");
            }
            add(connection, "01", "S1", "U1", "EMPLOYEE", "ai-q:old", "old question", false);
            add(connection, "02", "S1", null, "AI", "ai-a:old", "old answer", false);
            add(connection, "03", "S1", "U1", "EMPLOYEE", "ai-q:previous", "VPN cannot connect", false);
            add(connection, "04", "S1", null, "AI", "ai-a:previous", "Restart the VPN client", false);
            // These newer rows must not consume the LIMIT or appear in context.
            add(connection, "05", "S2", "U1", "EMPLOYEE", "ai-q:other", "other session", false);
            add(connection, "06", "S1", "U2", "EMPLOYEE", "ai-q:other-owner", "other owner", false);
            add(connection, "07", "S1", "U1", "EMPLOYEE", "human-1", "human conversation", false);
            add(connection, "08", "S1", "engineer", "ENGINEER", "ai-q:spoof", "engineer", false);
            add(connection, "09", "S1", null, "SYSTEM", "ai-a:spoof", "system", false);
            add(connection, "10", "S1", null, "AI", "other-ai", "unrelated AI", false);
            add(connection, "11", "S1", "U1", "EMPLOYEE", "ai-q:withdrawn", "withdrawn question", true);
            add(connection, "12", "S1", null, "AI", "ai-a:withdrawn", "withdrawn answer", true);
            add(connection, "13", "S1", null, "AI", "ai-a:empty", "", false);
            add(connection, "14", "S1", null, "AI", "ai-a:null", null, false);
            add(connection, "15", "S1", null, "AI", "ai-a:blank", " \r\n\t", false);
            add(connection, "16", "S1", "U1", "EMPLOYEE", "ai-q:current", "Restarted; still broken", false);
            // Prefixes alone are client controlled on the human-message endpoint.
            add(connection, "17", "S1", "U1", "EMPLOYEE", "ai-q:human-note", "private human conversation", false);
            // Even an AI answer must not reintroduce the content of a withdrawn question.
            add(connection, "18", "S1", "U1", "EMPLOYEE", "ai-q:removed-question", "withdrawn sensitive question", true);
            add(connection, "19", "S1", null, "AI", "ai-a:removed-question", "quotation of withdrawn question", false);
            Configuration config = new Configuration();
            config.setMapUnderscoreToCamelCase(true);
            config.addMapper(ConsultationMessageMapper.class);
            try (var session = new SqlSessionFactoryBuilder().build(config).openSession(connection)) {
                ConsultationMessageService service = new ConsultationMessageService(
                        session.getMapper(ConsultationMessageMapper.class), null, null, null, null, null);
                assertThat(service.loadAiHistory("S1", "U1", "ai-q:current", 2, 12000))
                        .containsExactly(new RagQuery.Turn("user", "VPN cannot connect"),
                                new RagQuery.Turn("assistant", "Restart the VPN client"));
                assertThat(service.loadAiHistory("S1", "U1", "ai-q:current", 3, 12000))
                        .extracting(RagQuery.Turn::content)
                        .containsExactly("old answer", "VPN cannot connect", "Restart the VPN client");
                assertThat(service.loadAiHistory("missing", "U1", "ai-q:current", 12, 12000)).isEmpty();
            }
        }
    }

    private void add(Connection connection, String id, String session, String sender, String role,
                     String clientId, String content, boolean withdrawn) throws Exception {
        try (var statement = connection.prepareStatement("INSERT INTO consultation_message VALUES (?, ?, ?, ?, ?, ?, ?, ?)")) {
            statement.setString(1, id);
            statement.setString(2, session);
            statement.setString(3, sender);
            statement.setString(4, role);
            statement.setString(5, clientId);
            statement.setString(6, content);
            statement.setTimestamp(7, Timestamp.valueOf(LocalDateTime.of(2026, 10, 8, 8, 0)
                    .plusSeconds(Integer.parseInt(id))));
            statement.setTimestamp(8, withdrawn ? Timestamp.valueOf(LocalDateTime.of(2026, 10, 8, 9, 0)) : null);
            statement.executeUpdate();
        }
    }
}
