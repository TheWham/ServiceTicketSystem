package com.itticket.rag;

import com.itticket.rag.dto.AiFeedbackCandidate;
import com.itticket.rag.mapper.AiFeedbackSourceMapper;
import org.apache.ibatis.session.Configuration;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.SelectProvider;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** 可选 MySQL 集成测试：仅使用连接私有临时表，绝不写现有业务表。 */
@EnabledIfEnvironmentVariable(named = "AI_FEEDBACK_MYSQL_TEST", matches = "true")
class AiFeedbackSourceMysqlTest {
    @Test void selectsOnlyHelpfulGeneralAnswersPairsByRequestAndExcludesCapturedSources() throws Exception {
        String url = System.getenv().getOrDefault("MYSQL_TEST_URL",
                "jdbc:mysql://120.92.138.195:3306/it_ticket_system?useSSL=false&allowPublicKeyRetrieval=true&characterEncoding=utf8");
        try (Connection connection = DriverManager.getConnection(url,
                System.getenv().getOrDefault("MYSQL_USERNAME", "root"), System.getenv("MYSQL_PASSWORD"))) {
            try (var sql = connection.createStatement()) {
                sql.execute("CREATE TEMPORARY TABLE consultation (session_id VARCHAR(64), creator_id VARCHAR(64), category_id VARCHAR(64))");
                sql.execute("CREATE TEMPORARY TABLE ai_interaction (interaction_id VARCHAR(64), session_id VARCHAR(64), feedback VARCHAR(32))");
                sql.execute("CREATE TEMPORARY TABLE consultation_message (session_id VARCHAR(64), sender_type VARCHAR(32), client_message_id VARCHAR(64), content TEXT, citation_json JSON, withdrawn_at DATETIME)");
                sql.execute("CREATE TEMPORARY TABLE knowledge_article (article_id VARCHAR(64))");
                sql.execute("INSERT INTO consultation VALUES ('S1', 'U1', 'C_NET'), ('S2', 'U2', 'C_HW')");
            }
            add(connection, "I1", "S1", "k1", "HELPFUL", "ANSWER", true, "[]", false);
            add(connection, "I2", "S1", "k2", "NOT_HELPFUL", "ANSWER", true, "[]", false);
            add(connection, "I3", "S1", "k3", "INCORRECT", "ANSWER", true, "[]", false);
            add(connection, "I4", "S1", "k4", "HELPFUL", "REFUSE", true, "[]", false);
            add(connection, "I5", "S1", "k5", "HELPFUL", "ANSWER", false, "[{}]", false);
            add(connection, "I6", "S1", "k6", "HELPFUL", "ANSWER", true, "[]", true);
            add(connection, "I7", "S2", "k1", "HELPFUL", "ANSWER", true, "[]", false);
            add(connection, "I8", "S1", "k8", "HELPFUL", "CLARIFY", false, "[]", false);
            add(connection, "I9", "S1", "k9", "HELPFUL", "ANSWER", true, "[{}]", false);
            // MySQL 同一 TEMPORARY TABLE 不能以两个别名重开。仅在测试复制问题表，
            // 查询沿用生产 @Select，仅替换第二次引用的物理表名。
            try (var sql = connection.createStatement()) {
                sql.execute("CREATE TEMPORARY TABLE feedback_test_questions AS SELECT * FROM consultation_message");
            }

            Configuration config = new Configuration();
            config.setMapUnderscoreToCamelCase(true);
            config.addMapper(TemporarySourceMapper.class);
            try (var session = new SqlSessionFactoryBuilder().build(config).openSession(connection)) {
                AiFeedbackSourceMapper source = session.getMapper(TemporarySourceMapper.class);
                var pending = source.findPending("", 100);
                assertThat(pending).extracting(AiFeedbackCandidate::interactionId).containsExactly("I1", "I7");
                assertThat(pending.get(0).question()).isEqualTo("question-S1-k1");
                assertThat(pending.get(0).answer()).isEqualTo("answer-I1");
                assertThat(pending.get(1).question()).isEqualTo("question-S2-k1");
                assertThat(source.findPending("I1", 100)).extracting(AiFeedbackCandidate::interactionId).containsExactly("I7");
                assertThat(source.findPending("", 1)).hasSize(1);
                try (var sql = connection.createStatement()) {
                    sql.execute("INSERT INTO knowledge_article VALUES (CONCAT('ai-', LEFT(SHA2('I1', 256), 60)))");
                }
                session.clearCache();
                assertThat(source.findPending("", 100)).extracting(AiFeedbackCandidate::interactionId).containsExactly("I7");
            }
        }
    }

    public interface TemporarySourceMapper extends AiFeedbackSourceMapper {
        @Override
        @SelectProvider(type = TemporarySql.class, method = "query")
        List<AiFeedbackCandidate> findPending(@Param("afterId") String afterId, @Param("batchSize") int batchSize);
    }

    public static class TemporarySql {
        public static String query() throws Exception {
            return String.join(" ", AiFeedbackSourceMapper.class.getMethod("findPending", String.class, int.class)
                    .getAnnotation(Select.class).value())
                    .replace("JOIN consultation_message q", "JOIN feedback_test_questions q");
        }
    }

    private void add(Connection connection, String id, String session, String key, String feedback,
                     String replyType, boolean general, String citations, boolean withdrawn) throws Exception {
        try (PreparedStatement statement = connection.prepareStatement("INSERT INTO ai_interaction VALUES (?, ?, ?)")) {
            statement.setString(1, id); statement.setString(2, session); statement.setString(3, feedback); statement.executeUpdate();
        }
        String metadata = "{\"interactionId\":\"" + id + "\",\"replyType\":\"" + replyType
                + "\",\"generalAnswer\":" + general + ",\"citations\":" + citations + "}";
        try (PreparedStatement statement = connection.prepareStatement(
                "INSERT INTO consultation_message VALUES (?, ?, ?, ?, ?, ?)")) {
            statement.setString(1, session); statement.setString(2, "AI"); statement.setString(3, "ai-a:" + key);
            statement.setString(4, "answer-" + id); statement.setString(5, metadata);
            statement.setTimestamp(6, withdrawn ? new java.sql.Timestamp(System.currentTimeMillis()) : null);
            statement.executeUpdate();
            statement.setString(2, "EMPLOYEE"); statement.setString(3, "ai-q:" + key);
            statement.setString(4, "question-" + session + "-" + key); statement.setString(5, null);
            statement.setTimestamp(6, null); statement.executeUpdate();
        }
    }
}
