package com.itticket.ticket.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.itticket.ticket.entity.Category;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.vo.TicketVO;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class PrdTicketContractTest {
    @Test void categoryOutputsCanonicalNatureAndStatus() {
        Category category = new Category(); category.setCategoryId("C01");
        category.setTicketNature("INCIDENT"); category.setStatus("ACTIVE");
        JsonNode json = new ObjectMapper().valueToTree(category);
        assertEquals("INCIDENT", json.path("ticket_nature").asText());
        assertEquals("ACTIVE", json.path("status").asText());
        assertFalse(json.has("enabled")); assertFalse(json.has("nature"));
    }
    @Test void ticketOutputsCanonicalSnapshotAndNature() {
        Ticket ticket = new Ticket(); ticket.setNature("INCIDENT"); ticket.setFieldDefinitionSnapshot("{\"serial\":\"123\"}");
        JsonNode json = new ObjectMapper().valueToTree(TicketVO.from(ticket));
        assertEquals("INCIDENT", json.path("nature").asText());
        assertEquals("{\"serial\":\"123\"}", json.path("field_definition_snapshot").asText());
        assertFalse(json.has("ticket_nature")); assertFalse(json.has("field_snapshot_json"));
    }
}
