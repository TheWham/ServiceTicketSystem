package com.itticket.rag;

import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.spring.MybatisSqlSessionFactoryBean;
import com.itticket.rag.config.MybatisPlusConfig;
import com.itticket.rag.entity.KnowledgeArticle;
import com.itticket.rag.enums.KnowledgeStatus;
import com.itticket.rag.mapper.KnowledgeArticleMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.jdbc.datasource.SingleConnectionDataSource;

import java.sql.DriverManager;

import static org.assertj.core.api.Assertions.assertThat;

/** 连接私有临时表验证列表投影，不写业务表。 */
@EnabledIfEnvironmentVariable(named = "AI_FEEDBACK_MYSQL_TEST", matches = "true")
class KnowledgeArticleListMysqlTest {
    @Test void currentVersionTitlesAreListedWithFallbackAndPaginationWithoutBodies() throws Exception {
        String url = System.getenv().getOrDefault("MYSQL_TEST_URL",
                "jdbc:mysql://120.92.138.195:3306/it_ticket_system?useSSL=false&allowPublicKeyRetrieval=true&characterEncoding=utf8");
        try (var connection = DriverManager.getConnection(url,
                System.getenv().getOrDefault("MYSQL_USERNAME", "root"), System.getenv("MYSQL_PASSWORD"))) {
            try (var sql = connection.createStatement()) {
                sql.execute("CREATE TEMPORARY TABLE knowledge_article (article_id VARCHAR(64) PRIMARY KEY, current_version_id VARCHAR(64), category_id VARCHAR(64), status VARCHAR(32), updated_at DATETIME)");
                sql.execute("CREATE TEMPORARY TABLE knowledge_version (version_id VARCHAR(64) PRIMARY KEY, article_id VARCHAR(64), content JSON)");
                sql.execute("INSERT INTO knowledge_article VALUES ('A1','V2','C_NET','PENDING_REVIEW',NOW()),('A2','V3','C_NET','PENDING_REVIEW',NOW()),('A3',NULL,'C_HW','DRAFT',NOW()),('A4','V4','C_NET','PENDING_REVIEW',NOW())");
                sql.execute("""
                    INSERT INTO knowledge_version VALUES
                    ('V1','A1','{"title":"旧标题"}'),
                    ('V2','A1','{"title":"VPN 连接问题排查","body":"不应返回列表的正文"}'),
                    ('V3','A2','{"title":"  "}'),
                    ('V4','A4','{"title":null}')
                    """);
            }
            var factory = new MybatisSqlSessionFactoryBean();
            var config = new MybatisConfiguration();
            config.setMapUnderscoreToCamelCase(true);
            config.addMapper(KnowledgeArticleMapper.class);
            factory.setConfiguration(config);
            factory.setDataSource(new SingleConnectionDataSource(connection, true));
            factory.setPlugins(new MybatisPlusConfig().mybatisPlusInterceptor());
            var mapper = new SqlSessionTemplate(factory.getObject()).getMapper(KnowledgeArticleMapper.class);

            var filter = new LambdaQueryWrapper<KnowledgeArticle>()
                    .eq(KnowledgeArticle::getStatus, KnowledgeStatus.PENDING_REVIEW)
                    .eq(KnowledgeArticle::getCategoryId, "C_NET")
                    .orderByAsc(KnowledgeArticle::getArticleId);
            var first = mapper.selectPageWithTitles(new Page<>(1, 2), filter);
            assertThat(first.getTotal()).isEqualTo(3);
            assertThat(first.getRecords()).extracting(KnowledgeArticle::getTitle)
                    .containsExactly("VPN 连接问题排查", "（未命名知识）");
            var second = mapper.selectPageWithTitles(new Page<>(2, 2), filter);
            assertThat(second.getRecords()).extracting(KnowledgeArticle::getTitle).containsExactly("（未命名知识）");
            var missingVersion = mapper.selectPageWithTitles(new Page<>(1, 10),
                    new LambdaQueryWrapper<KnowledgeArticle>().eq(KnowledgeArticle::getArticleId, "A3"));
            assertThat(missingVersion.getRecords().get(0).getTitle()).isEqualTo("（未命名知识）");
            String json = new com.fasterxml.jackson.databind.ObjectMapper().findAndRegisterModules().writeValueAsString(first);
            assertThat(json).contains("VPN 连接问题排查").doesNotContain("不应返回列表的正文", "旧标题");
        }
    }
}
