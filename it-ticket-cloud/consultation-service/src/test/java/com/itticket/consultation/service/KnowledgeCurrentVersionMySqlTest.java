package com.itticket.consultation.service;

import com.itticket.consultation.mapper.KnowledgeQueryMapper;
import com.itticket.consultation.adapter.RagResult;
import com.itticket.consultation.adapter.RagStatus;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.enums.AiRefusalReason;
import com.itticket.consultation.enums.AiReplyType;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.mybatis.spring.SqlSessionFactoryBean;
import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;
import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Opt-in integration tests; only an explicitly named disposable local MySQL database is accepted. */
@EnabledIfEnvironmentVariable(named = "RAG_COMPOSITION_TEST_MYSQL_URL",
        matches = "jdbc:mysql://(127\\.0\\.0\\.1|localhost):[0-9]+/rag_composition_test[a-zA-Z0-9_]*(\\?.*)?")
class KnowledgeCurrentVersionMySqlTest {
    private DriverManagerDataSource dataSource;
    private JdbcTemplate jdbc;
    private JdbcTemplate concurrentJdbc;
    private SqlSessionFactory sessions;
    private KnowledgeQueryService knowledge;
    private TransactionTemplate transaction;

    @BeforeEach
    void setUp() throws Exception {
        String url = System.getenv("RAG_COMPOSITION_TEST_MYSQL_URL");
        String user = System.getenv().getOrDefault("RAG_COMPOSITION_TEST_MYSQL_USER", "root");
        String password = System.getenv().getOrDefault("RAG_COMPOSITION_TEST_MYSQL_PASSWORD", "");
        dataSource = new DriverManagerDataSource(url, user, password);
        jdbc = new JdbcTemplate(dataSource);
        concurrentJdbc = new JdbcTemplate(new DriverManagerDataSource(url, user, password));
        jdbc.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_article (
                    article_id VARCHAR(64) PRIMARY KEY,
                    current_version_id VARCHAR(64) NOT NULL,
                    status VARCHAR(32) NOT NULL
                ) ENGINE=InnoDB
                """);
        jdbc.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_version (
                    version_id VARCHAR(64) PRIMARY KEY,
                    article_id VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB
                """);
        jdbc.update("DELETE FROM knowledge_version");
        jdbc.update("DELETE FROM knowledge_article");
        jdbc.update("INSERT INTO knowledge_article VALUES ('A1', 'V1', 'PUBLISHED')");
        jdbc.update("INSERT INTO knowledge_version VALUES ('V1', 'A1')");

        var factory = new SqlSessionFactoryBean();
        factory.setDataSource(dataSource);
        sessions = factory.getObject();
        sessions.getConfiguration().addMapper(KnowledgeQueryMapper.class);
        knowledge = new KnowledgeQueryService(new SqlSessionTemplate(sessions).getMapper(KnowledgeQueryMapper.class));
        transaction = new TransactionTemplate(new DataSourceTransactionManager(dataSource));
        transaction.setIsolationLevel(TransactionDefinition.ISOLATION_REPEATABLE_READ);
    }

    @Test
    void finalVerificationSeesCommittedOfflineStateDespiteExistingRepeatableReadSnapshot() {
        transaction.executeWithoutResult(status -> {
            assertThat(articleStatus(jdbc)).isEqualTo("PUBLISHED");
            concurrentJdbc.update("UPDATE knowledge_article SET status='OFFLINE' WHERE article_id='A1'");
            assertThat(articleStatus(jdbc)).isEqualTo("PUBLISHED");

            assertThat(knowledge.isPublishedCurrentVersion("A1", "V1")).isFalse();
        });
    }

    @Test
    void repeatedVerificationInOneSqlSessionDoesNotReuseCachedPublishedResult() {
        try (SqlSession session = sessions.openSession(true)) {
            var sameSessionKnowledge = new KnowledgeQueryService(session.getMapper(KnowledgeQueryMapper.class));
            assertThat(sameSessionKnowledge.isPublishedCurrentVersion("A1", "V1")).isTrue();
            concurrentJdbc.update("UPDATE knowledge_article SET status='OFFLINE' WHERE article_id='A1'");

            assertThat(sameSessionKnowledge.isPublishedCurrentVersion("A1", "V1")).isFalse();
        }
    }

    @Test
    void verifiedPublishedVersionStaysLockedUntilAnswerTransactionCompletes() {
        transaction.executeWithoutResult(status -> {
            assertThat(knowledge.isPublishedCurrentVersion("A1", "V1")).isTrue();
            assertThatThrownBy(() -> {
                try (Connection writer = dataSource.getConnection(); Statement statement = writer.createStatement()) {
                    statement.execute("SET SESSION innodb_lock_wait_timeout=1");
                    statement.executeUpdate("UPDATE knowledge_article SET status='OFFLINE' WHERE article_id='A1'");
                }
            }).isInstanceOf(SQLException.class).satisfies(failure ->
                    assertThat(((SQLException) failure).getErrorCode()).isEqualTo(1205));
        });
        assertThat(concurrentJdbc.update("UPDATE knowledge_article SET status='OFFLINE' WHERE article_id='A1'"))
                .isEqualTo(1);
    }

    @Test
    void competingKnowledgeUpdateImmediatelyRefusesAsDependencyUnavailable() throws SQLException {
        try (Connection writer = dataSource.getConnection(); Statement statement = writer.createStatement()) {
            writer.setAutoCommit(false);
            try {
                statement.executeUpdate("UPDATE knowledge_article SET status='OFFLINE' WHERE article_id='A1'");
                RagResult answer = new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, "检查输入设备。",
                        List.of(new KnowledgeCitationDto("A1", "V1", "排障", BigDecimal.ONE, "检查输入设备。")),
                        BigDecimal.ONE, null, "test", List.of("V1"), 0, null, false, false);
                long started = System.nanoTime();
                AiAnswerGuard.Verdict verdict = transaction.execute(status ->
                        AiAnswerGuard.evaluate(answer, new ConsultationProperties().getAi(),
                                knowledge::isPublishedCurrentVersion));

                assertThat(verdict.refusalReason()).isEqualTo(AiRefusalReason.MODEL_UNAVAILABLE);
                assertThat((System.nanoTime() - started) / 1_000_000).isLessThan(2000);
            } finally {
                writer.rollback();
            }
        }
    }

    private static String articleStatus(JdbcTemplate database) {
        return database.queryForObject("SELECT status FROM knowledge_article WHERE article_id='A1'", String.class);
    }
}
