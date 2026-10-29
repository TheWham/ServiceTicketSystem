package com.itticket.ticket.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

import java.util.List;

/**
 * 提单人编辑工单请求 —— 与创建工单字段一致（§10.2 固定字段）。
 * 仅允许在 NEW / ASSIGNED / PENDING_SUPPLEMENT 状态下编辑；
 * 附件为「编辑后期望保留的完整 id 列表」（全量语义）。
 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class UpdateTicketRequest {
    /** 工单性质 INCIDENT/SERVICE_REQUEST（必填） */
    private String nature;
    /** 末级分类 id（必填，必须为启用末级分类） */
    private String categoryId;
    /** 标题 1~100 字符（必填） */
    private String title;
    /** 问题描述 1~5000 字符（必填） */
    private String description;
    /** 影响情况（必填，供工程师确认影响范围） */
    private String impactDescription;
    /** 紧急说明（必填，供工程师确认紧急程度） */
    private String urgencyDescription;
    /** 办公地点（选填） */
    private String location;
    /** 本次联系方式（选填） */
    private String contact;
    /** 资产编号（选填，硬件建议填） */
    private String assetId;
    /** 编辑后保留的附件 id 全量列表（选填；不传则不改动附件） */
    private List<String> attachments;
}
