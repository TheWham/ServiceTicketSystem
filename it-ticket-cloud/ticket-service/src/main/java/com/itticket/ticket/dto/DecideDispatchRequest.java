package com.itticket.ticket.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;

/**
 * 裁决请求体 —— 派单草案与异常队列共用的最小裁决契约。
 *
 * <p>审批人确认（approve=true）后草案才真正落 assignment；驳回（approve=false）
 * 必须给出原因，业务对象回到待处理状态，不做任何静默改派。
 *
 * <p>异常队列结案时用 {@code resolution} 显式给出终态（RESOLVED / DISMISSED）。
 */
@JsonPropertyOrder({"approve", "resolution", "reason"})
public record DecideDispatchRequest(
        /** approve=true 放行（派单草案）/ 视为已处理（异常） */
        @JsonProperty("approve") boolean approve,
        /** 异常结案专用终态：RESOLVED 或 DISMISSED；派单草案不使用 */
        @JsonProperty("resolution") String resolution,
        /** 驳回或结案必填；放行时作为备注留痕 */
        @JsonProperty("reason") String reason) {
}