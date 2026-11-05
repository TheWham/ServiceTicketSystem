package com.itticket.consultation.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * Model Router 动态选模与成本治理全景调用链路 Trace (DeepSeek Harness 规范)。
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record GovernanceTraceDto(
        @JsonProperty("traceId") String traceId,
        @JsonProperty("chosenTier") String chosenTier,
        @JsonProperty("chosenModel") String chosenModel,
        @JsonProperty("routingReason") String routingReason,
        @JsonProperty("riskScore") BigDecimal riskScore,
        @JsonProperty("intent") String intent,
        @JsonProperty("totalTokens") Integer totalTokens,
        @JsonProperty("promptTokens") Integer promptTokens,
        @JsonProperty("completionTokens") Integer completionTokens,
        @JsonProperty("totalLatencyMs") BigDecimal totalLatencyMs,
        @JsonProperty("actualCostRmb") BigDecimal actualCostRmb,
        @JsonProperty("savedVsPremiumRmb") BigDecimal savedVsPremiumRmb,
        @JsonProperty("savingsRatePercent") BigDecimal savingsRatePercent,
        @JsonProperty("isDegraded") Boolean isDegraded,
        @JsonProperty("degradationReason") String degradationReason,
        @JsonProperty("stages") List<Map<String, Object>> stages) {
}
