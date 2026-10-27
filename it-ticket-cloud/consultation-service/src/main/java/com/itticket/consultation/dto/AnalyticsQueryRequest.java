package com.itticket.consultation.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 跨工单分析请求（AI-API 扩展）。
 *
 * <p>刻意只有 {@code question} 一个入参：时间范围、设备范围、聚合维度全部由
 * Python 分析链路从问题文本里解析（模型抽语义槽位、词表与正则兜底），不由调用方传参。
 * 让前端传结构化的 window/scope 会打开一条"绕过解析直接指定统计口径"的口子，
 * 那正是这条链路要收口的东西。
 *
 * <p>身份（userId/role）也不在请求体里 —— 从认证上下文取，调用方无法自报。
 */
public record AnalyticsQueryRequest(@NotBlank @Size(max = 2000) String question) {
}