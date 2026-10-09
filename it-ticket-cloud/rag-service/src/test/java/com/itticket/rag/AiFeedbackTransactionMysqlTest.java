package com.itticket.rag;

import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.extension.spring.MybatisSqlSessionFactoryBean;
import com.itticket.rag.config.MybatisPlusConfig;
import com.itticket.rag.dto.AiFeedbackCandidate;
import com.itticket.rag.entity.OutboxEvent;
import com.itticket.rag.mapper.*;
import com.itticket.rag.service.AiFeedbackKnowledgeService;
import com.itticket.rag.service.KnowledgeStore;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.aop.framework.ProxyFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.SingleConnectionDataSource;
import org.springframework.transaction.annotation.AnnotationTransactionAttributeSource;
import org.springframework.transaction.interceptor.TransactionInterceptor;

import java.sql.DriverManager;
import java.util.concurrent.atomic.AtomicBoolean;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/** 使用现有库表结构的连接私有临时副本验证真实 Spring/MySQL 事务，无业务数据写入。 */
@EnabledIfEnvironmentVariable(named = "AI_FEEDBACK_MYSQL_TEST", matches = "true")
class AiFeedbackTransactionMysqlTest {
    @Test void failedOutboxWriteRollsBackAllKnowledgeRowsAndRetryCreatesExactlyOneReview() throws Exception {
        String url = System.getenv().getOrDefault("MYSQL_TEST_URL",
                "jdbc:mysql://120.92.138.195:3306/it_ticket_system?useSSL=false&allowPublicKeyRetrieval=true&characterEncoding=utf8");
        try (var connection = DriverManager.getConnection(url,
                System.getenv().getOrDefault("MYSQL_USERNAME", "root"), System.getenv("MYSQL_PASSWORD"))) {
            String[] tables = {"knowledge_article", "knowledge_version", "knowledge_transition", "outbox_event"};
            try (var sql = connection.createStatement()) {
                for (String table : tables) {
                    String ddl;
                    try (var result = sql.executeQuery("SHOW CREATE TABLE " + table)) {
                        result.next();
                        ddl = result.getString(2).replaceFirst("CREATE TABLE", "CREATE TEMPORARY TABLE");
                        // MySQL 临时表不支持全文索引；保留字段、唯一键和检查约束。
                        ddl = ddl.replaceAll("(?m)^\\s*FULLTEXT KEY[^\\r\\n]*\\R?", "")
                                .replaceAll(",\\s*\\)", "\n)");
                    }
                    sql.execute(ddl);
                }
            }
            var dataSource = new SingleConnectionDataSource(connection, true);
            var factory = new MybatisSqlSessionFactoryBean();
            var config = new MybatisConfiguration();
            config.setMapUnderscoreToCamelCase(true);
            config.addMapper(KnowledgeArticleMapper.class);
            config.addMapper(KnowledgeVersionMapper.class);
            config.addMapper(KnowledgeTransitionMapper.class);
            config.addMapper(OutboxEventMapper.class);
            factory.setConfiguration(config);
            factory.setDataSource(dataSource);
            factory.setPlugins(new MybatisPlusConfig().mybatisPlusInterceptor());
            var session = new SqlSessionTemplate(factory.getObject());
            var articles = session.getMapper(KnowledgeArticleMapper.class);
            var versions = session.getMapper(KnowledgeVersionMapper.class);
            var transitions = session.getMapper(KnowledgeTransitionMapper.class);
            var realEvents = session.getMapper(OutboxEventMapper.class);
            var events = mock(OutboxEventMapper.class);
            AtomicBoolean fail = new AtomicBoolean(true);
            when(events.insert(any(OutboxEvent.class))).thenAnswer(call -> {
                int rows = realEvents.insert((OutboxEvent) call.getArgument(0));
                if (fail.get()) throw new IllegalStateException("injected failure after outbox insert");
                return rows;
            });
            var store = new KnowledgeStore(articles, versions, transitions, events);
            var proxy = new ProxyFactory(new AiFeedbackKnowledgeService(articles, versions, store));
            proxy.addAdvice(new TransactionInterceptor(new DataSourceTransactionManager(dataSource),
                    new AnnotationTransactionAttributeSource()));
            var service = (AiFeedbackKnowledgeService) proxy.getProxy();
            var candidate = new AiFeedbackCandidate("TX1", "CS1", "U1", "C_NET", "无线网络连不上怎么办？", "请检查飞行模式并重新连接无线网络。");
            var jdbc = new JdbcTemplate(dataSource);

            assertThatThrownBy(() -> service.capture(candidate)).isInstanceOf(IllegalStateException.class);
            for (String table : tables) assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM " + table, Integer.class)).isZero();
            fail.set(false);
            assertThat(service.capture(candidate)).isTrue();
            assertThat(service.capture(candidate)).isFalse();
            for (String table : tables) assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM " + table, Integer.class)).isEqualTo(1);
            assertThat(jdbc.queryForObject("SELECT status FROM knowledge_article", String.class)).isEqualTo("PENDING_REVIEW");
            assertThat(jdbc.queryForObject("SELECT event_type FROM outbox_event", String.class)).isEqualTo("KNOWLEDGE_SUBMITTED");
        }
    }
}
