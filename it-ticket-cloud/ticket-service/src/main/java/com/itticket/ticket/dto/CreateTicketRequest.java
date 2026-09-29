package com.itticket.ticket.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * 创建工单请求 —— PRD §10.2 固定字段严格对齐。
 * 不接收 priority（新单默认 MEDIUM，接单按 §11.4 矩阵确认）；
 * 不接收 expected_finish_time（PRD 无此字段）；幂等键为 idempotency_key（§10.4）。
 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class CreateTicketRequest {
    /** 工单性质 INCIDENT/SERVICE_REQUEST（必填） */
    @JsonAlias("ticket_nature")
    private String nature;
    /** 末级分类 id（必填，必须为启用末级分类） */
    private String categoryId;
    /** 标题 1~100 字符（必填） */
    private String title;
    /** 问题描述 10~5000 字符（必填） */
    private String description;
    /** 影响情况（必填，供工程师确认影响范围） */
    private String impactDescription;
    /** 紧急说明（必填，供工程师确认紧急程度） */
    private String urgencyDescription;
    /** 办公地点（选填） */
    private String location;
    /** 本次联系方式（选填，默认来自身份源） */
    private String contact;
    /** 资产编号（选填，硬件建议填） */
    private String assetId;
    /** 附件 URL 列表（选填） */
    private List<String> attachments;
    /** 来源咨询会话 id（咨询转单时系统写入） */
    private String sourceSessionId;
    /** 提单幂等键（§10.4，防重复提交） */
    private String idempotencyKey;
    /** Consultation/category context captured at submission. */
    private Map<String, Object> fieldValues;
}
