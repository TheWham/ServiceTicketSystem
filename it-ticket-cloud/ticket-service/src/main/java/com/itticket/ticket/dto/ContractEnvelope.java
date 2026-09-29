package com.itticket.ticket.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;

/**
 * spec 05 统一响应包络(PRD 21.1):{code, message, request_id, data}。
 * 新契约端点(建单、草稿)使用;旧端点保持 legacy Result({code:int, msg})。
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@JsonPropertyOrder({"code", "message", "request_id", "data"})
public record ContractEnvelope<T>(
        String code,
        String message,
        @JsonProperty("request_id") String requestId,
        T data) {

    public static <T> ContractEnvelope<T> ok(String requestId, String message, T data) {
        return new ContractEnvelope<>("SUCCESS", message, requestId, data);
    }
}
