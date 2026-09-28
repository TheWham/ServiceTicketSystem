package com.itticket.ticket.vo;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.AllArgsConstructor;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 已完成工单摘要(供 ai-service 知识回流同步拉取)。
 * solutionRemark 取自最后一条流转到「已完成」的处理记录备注,即工程师的解决方案。
 */
@Data
@AllArgsConstructor
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class SolvedTicketVO {
    private String ticketId;
    private String title;
    private String category;
    private String description;
    /** 工程师处理结论(可能为空) */
    private String solutionRemark;
    private LocalDateTime solvedAt;
}
