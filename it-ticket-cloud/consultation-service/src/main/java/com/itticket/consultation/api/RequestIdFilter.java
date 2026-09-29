package com.itticket.consultation.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.annotation.Order;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * X-Request-Id 校验与透传(AI-002:请求必须带 X-Request-Id;OpenAPI 05 将其声明为 required)。
 *
 * <p>只对 {@code /api/v1/**} 强制;健康检查等非契约路径放行并使用占位 ID。
 * 响应回写同一 ID,便于客户端与服务端日志对账(RD-010)。
 */
@Component
@Order(-100)
public class RequestIdFilter extends OncePerRequestFilter {

    public static final String HEADER = "X-Request-Id";
    private static final int MAX_LENGTH = 128;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String requestId = request.getHeader(HEADER);
        boolean contractPath = request.getRequestURI().startsWith("/api/v1/");

        if (contractPath && (requestId == null || requestId.isBlank() || requestId.length() > MAX_LENGTH)) {
            writeMissingHeader(response);
            return;
        }
        if (requestId == null || requestId.isBlank()) {
            // 非契约路径缺头时生成一次性 ID,而不是固定常量:
            // audit_log.request_id 是 NOT NULL,常量会让并发请求共享同一 ID,破坏 RD-010 的对账链。
            requestId = "req_" + java.util.UUID.randomUUID().toString().replace("-", "");
        }

        RequestContext.set(requestId);
        response.setHeader(HEADER, requestId);
        try {
            chain.doFilter(request, response);
        } finally {
            RequestContext.clear();
        }
    }

    private void writeMissingHeader(HttpServletResponse response) throws IOException {
        ApiEnvelope<Void> body = ApiEnvelope.error(
                ApiCode.VALIDATION_ERROR, ApiCode.VALIDATION_ERROR.getDefaultMessage(), "req_missing",
                List.of(FieldIssue.required(HEADER, "请求必须携带 X-Request-Id 请求头")), null);
        response.setStatus(ApiCode.VALIDATION_ERROR.getHttpStatus());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding("UTF-8");
        objectMapper.writeValue(response.getOutputStream(), body);
    }
}
