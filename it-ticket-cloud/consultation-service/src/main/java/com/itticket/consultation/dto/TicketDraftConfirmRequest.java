package com.itticket.consultation.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 员工确认建单请求(人机回环第二步)。
 *
 * <p>员工在前端可编辑 AI 草稿后再确认;服务端重新校验字段并绑定当前登录员工为 creator,
 * 不接受请求体指定 creator(归属安全 AX-001)。
 */
public record TicketDraftConfirmRequest(
        @NotBlank @Size(max = 100) String title,
        @Size(max = 64) String category,
        @NotBlank @Size(max = 2000) String description,
        @Size(max = 16) String priority) {
}
