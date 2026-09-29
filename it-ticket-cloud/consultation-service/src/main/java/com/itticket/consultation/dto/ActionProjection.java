package com.itticket.consultation.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;

/** OpenAPI 05 ActionProjection。用于无对象返回值的动作类接口。 */
@JsonPropertyOrder({"operation_id", "accepted"})
public record ActionProjection(
        @JsonProperty("operation_id") String operationId,
        boolean accepted) {
}
