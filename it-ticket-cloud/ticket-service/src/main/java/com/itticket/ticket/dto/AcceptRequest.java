package com.itticket.ticket.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

/**
 * 接单请求 —— PRD §9.3 接单边「确认影响与紧急程度」+ §11.4 矩阵算正式优先级。
 * 工程师不能绕过矩阵直接指定优先级。
 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class AcceptRequest {
    /** 影响范围 SINGLE/DEPARTMENT/CROSS_DEPT（必填） */
    private String impactScope;
    /** 紧急程度 LOW/MEDIUM/HIGH（必填） */
    private String urgencyLevel;
}
