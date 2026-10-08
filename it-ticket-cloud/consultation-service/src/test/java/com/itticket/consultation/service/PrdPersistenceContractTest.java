package com.itticket.consultation.service;

import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.core.metadata.TableInfoHelper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.consultation.entity.*;
import com.itticket.consultation.enums.ConsultationResolutionType;
import com.itticket.consultation.mapper.KnowledgeQueryMapper;
import org.apache.ibatis.builder.MapperBuilderAssistant;
import org.junit.jupiter.api.Test;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;

/**
 * 持久化层列名契约回归：
 *  - 实体属性必须显式绑定规范列名（resolved_type / breach_at / content / retrieved_versions /
 *    latency / before_value / after_value），防驼峰推断写错列；
 *  - 对外 JSON 输出 resolved_type（旧 resolution_type 不得出现）；
 *  - 知识检索 SQL 必须查询规范 content 列的 JSON_EXTRACT，不得查询历史 content_json。
 * 本类同时借助 MyBatis-Plus 元数据与原生 MyBatis MappedStatement 直接渲染 SQL 文本，覆盖了
 * “构建期即可暴露问题”的路线，避免问题拖到线上 SQL 执行时报 Unknown column。
 */
class PrdPersistenceContractTest {

    /** 实体 -> 规范列名逐对核对（利用 TableInfoHelper 元数据，无需数据库连接） */
    @Test
    void persistenceSelectsPrdColumnsForExistingEntities() {
        assertColumn(Consultation.class, "resolutionType", "resolved_type");
        assertColumn(SlaInstance.class, "breachedAt", "breach_at");
        assertColumn(KnowledgeVersion.class, "contentJson", "content");
        assertColumn(AiInteraction.class, "retrievedVersionsJson", "retrieved_versions");
        assertColumn(AiInteraction.class, "latencyMs", "latency");
        assertColumn(AuditLog.class, "beforeJson", "before_value");
        assertColumn(AuditLog.class, "afterJson", "after_value");
    }

    /** 初始化实体元数据并断言指定属性映射到期望列名 */
    private void assertColumn(Class<?> entity, String property, String column) {
        var table = TableInfoHelper.initTableInfo(new MapperBuilderAssistant(new MybatisConfiguration(), "test"), entity);
        assertEquals(column, table.getFieldList().stream()
                .filter(f -> f.getProperty().equals(property)).findFirst().orElseThrow().getColumn());
    }

    /** 会话实体序列化：规范键 resolved_type 出现，旧键 resolution_type / 驼峰键都不得出现 */
    @Test
    void consultationProjectionUsesResolvedType() {
        Consultation consultation = new Consultation();
        consultation.setResolutionType(ConsultationResolutionType.EMPLOYEE_CONFIRMED);
        var json = new ObjectMapper().valueToTree(consultation);
        assertEquals("EMPLOYEE_CONFIRMED", json.path("resolved_type").asText());
        assertFalse(json.has("resolution_type"));
        assertFalse(json.has("resolutionType"));
    }

    /**
     * 知识检索 SQL 文本契约：retrieveByFulltext / retrieveByLike / searchPage 三个语句
     * 都必须渲染为 JSON_EXTRACT(v.content, ...)；反查 v.content_json 绝不允许出现。
     * 用纯 Configuration 渲染 MappedStatement（带参数绑定走通路径），不依赖数据库。
     */
    @Test
    void knowledgeRetrievalRendersSqlAgainstContentColumn() {
        MybatisConfiguration configuration = new MybatisConfiguration();
        configuration.addMapper(KnowledgeQueryMapper.class);
        for (String method : new String[]{"retrieveByFulltext", "retrieveByLike", "searchPage"}) {
            String sql = configuration.getMappedStatement(KnowledgeQueryMapper.class.getName() + "." + method)
                    .getBoundSql(Map.of("keyword", "VPN", "pattern", "VPN", "categoryId", "C01", "limit", 5, "offset", 0))
                    .getSql();
            assertTrue(sql.contains("JSON_EXTRACT(v.content,"));
            assertFalse(sql.contains("v.content_json"));
        }
    }
}