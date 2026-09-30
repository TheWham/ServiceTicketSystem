package com.itticket.ticket.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.itticket.ticket.entity.Category;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.vo.TicketVO;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * 工单域对外 JSON 契约的规范命名回归：
 *  - 分类实体输出 ticket_nature（分类默认工单性质）+ status；
 *  - 工单 VO 输出 nature（工单实际性质）+ field_definition_snapshot（动态表单快照）；
 *  - 历史命名（enabled / nature 错位 / field_snapshot_json）绝不允许回潮 ——
 *    前端字段归一化曾因此处 snake/camel 错位导致“问题分类下拉为空”的线上缺陷。
 */
class PrdTicketContractTest {

    /**
     * 分类（Category）输出契约：
     * ticket_nature 表示“该分类创建工单的默认性质”，status 表示分类启停用；
     * 不得出现 enabled（旧布尔命名）或裸 nature（会与工单实体的 nature 混淆）。
     */
    @Test
    void categoryOutputsCanonicalNatureAndStatus() {
        Category category = new Category();
        category.setCategoryId("C01");
        category.setTicketNature("INCIDENT");
        category.setStatus("ACTIVE");
        JsonNode json = new ObjectMapper().valueToTree(category);
        assertEquals("INCIDENT", json.path("ticket_nature").asText());
        assertEquals("ACTIVE", json.path("status").asText());
        assertFalse(json.has("enabled"));
        assertFalse(json.has("nature"));
    }

    /**
     * 工单（TicketVO）输出契约：
     * nature 为工单实际性质（来自 ticket.nature 列），
     * field_definition_snapshot 原样透传建单时的表单定义快照 JSON；
     * 反向断言旧字段名 ticket_nature / field_snapshot_json 不再出现。
     */
    @Test
    void ticketOutputsCanonicalSnapshotAndNature() {
        Ticket ticket = new Ticket();
        ticket.setNature("INCIDENT");
        ticket.setFieldDefinitionSnapshot("{\"serial\":\"123\"}");
        JsonNode json = new ObjectMapper().valueToTree(TicketVO.from(ticket));
        assertEquals("INCIDENT", json.path("nature").asText());
        assertEquals("{\"serial\":\"123\"}", json.path("field_definition_snapshot").asText());
        assertFalse(json.has("ticket_nature"));
        assertFalse(json.has("field_snapshot_json"));
    }
}