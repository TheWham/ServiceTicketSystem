package com.itticket.rag;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.rag.vo.RetrievedChunk;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 8302 直通层的图扩展三字段用例(Task 12 计划明文修正项):
 * python 检索内核返回的 graphExpanded/expandedFrom/relation 不得被
 * PythonRetrievalClient 的 treeToValue DTO 绑定丢弃,经 8302 再序列化给
 * consultation 侧时 camelCase 原样在场;缺省时三键在 wire 上完全缺席。
 */
class RetrievedChunkGraphFieldTest {

    private final ObjectMapper json = new ObjectMapper();

    @Test
    void treeToValueBindingKeepsGraphFieldsFromPythonKernel() throws Exception {
        String wire = "{\"chunkId\":\"ITKB-ACC-002#c1\",\"articleId\":\"art-1001\",\"versionId\":\"ver-2001\","
                + "\"title\":\"密码重置\",\"snippet\":\"片段\",\"content\":\"全文\",\"categoryId\":\"C_ACC\","
                + "\"score\":0.40,\"indexVersion\":\"ver-2001\","
                + "\"graphExpanded\":true,\"expandedFrom\":\"ITKB-ACC-002\",\"relation\":\"RELATED\"}";
        RetrievedChunk it = json.treeToValue(json.readTree(wire), RetrievedChunk.class);
        assertThat(it.graphExpanded()).isTrue();
        assertThat(it.expandedFrom()).isEqualTo("ITKB-ACC-002");
        assertThat(it.relation()).isEqualTo("RELATED");
        // 经 8302 再序列化给 consultation 侧:三键仍以 camelCase 在场
        assertThat(json.writeValueAsString(it))
                .contains("\"graphExpanded\":true")
                .contains("\"expandedFrom\":\"ITKB-ACC-002\"")
                .contains("\"relation\":\"RELATED\"");
    }

    @Test
    void graphFieldsAreAbsentWhenUnset() throws Exception {
        RetrievedChunk it = new RetrievedChunk("ITKB-ACC-002#c1", "art-1001", "ver-2001",
                "密码重置", "片段", "全文", "C_ACC", new BigDecimal("0.82"), "ver-2001",
                null, null, null);
        assertThat(json.writeValueAsString(it))
                .doesNotContain("graphExpanded", "expandedFrom", "relation");
    }

    @Test
    void unsetGraphFieldsBindToNull() throws Exception {
        String wire = "{\"chunkId\":\"c1\",\"articleId\":\"art-1\",\"versionId\":\"v1\","
                + "\"title\":\"标题\",\"snippet\":\"片段\",\"content\":\"全文\",\"categoryId\":\"C_ACC\","
                + "\"score\":0.5,\"indexVersion\":\"v1\"}";
        RetrievedChunk it = json.treeToValue(json.readTree(wire), RetrievedChunk.class);
        assertThat(it.graphExpanded()).isNull();
        assertThat(it.expandedFrom()).isNull();
        assertThat(it.relation()).isNull();
    }
}
