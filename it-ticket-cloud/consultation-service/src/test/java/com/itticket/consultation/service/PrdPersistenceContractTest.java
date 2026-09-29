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

class PrdPersistenceContractTest {
    @Test void persistenceSelectsPrdColumnsForExistingEntities() {
        assertColumn(Consultation.class, "resolutionType", "resolved_type");
        assertColumn(SlaInstance.class, "breachedAt", "breach_at");
        assertColumn(KnowledgeVersion.class, "contentJson", "content");
        assertColumn(AiInteraction.class, "retrievedVersionsJson", "retrieved_versions");
        assertColumn(AiInteraction.class, "latencyMs", "latency");
        assertColumn(AuditLog.class, "beforeJson", "before_value");
        assertColumn(AuditLog.class, "afterJson", "after_value");
    }
    private void assertColumn(Class<?> entity, String property, String column) {
        var table = TableInfoHelper.initTableInfo(new MapperBuilderAssistant(new MybatisConfiguration(), "test"), entity);
        assertEquals(column, table.getFieldList().stream().filter(f -> f.getProperty().equals(property)).findFirst().orElseThrow().getColumn());
    }
    @Test void consultationProjectionUsesResolvedType() {
        Consultation consultation = new Consultation();
        consultation.setResolutionType(ConsultationResolutionType.EMPLOYEE_CONFIRMED);
        var json = new ObjectMapper().valueToTree(consultation);
        assertEquals("EMPLOYEE_CONFIRMED", json.path("resolved_type").asText());
        assertFalse(json.has("resolution_type")); assertFalse(json.has("resolutionType"));
    }
    @Test void knowledgeRetrievalRendersSqlAgainstContentColumn() {
        MybatisConfiguration configuration = new MybatisConfiguration();
        configuration.addMapper(KnowledgeQueryMapper.class);
        for (String method : new String[]{"retrieveByFulltext", "retrieveByLike", "searchPage"}) {
            String sql = configuration.getMappedStatement(KnowledgeQueryMapper.class.getName() + "." + method)
                    .getBoundSql(Map.of("keyword", "VPN", "pattern", "VPN", "categoryId", "C01", "limit", 5, "offset", 0)).getSql();
            assertTrue(sql.contains("JSON_EXTRACT(v.content,")); assertFalse(sql.contains("v.content_json"));
        }
    }
}
