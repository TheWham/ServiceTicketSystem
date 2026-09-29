package com.itticket.consultation.api;

import com.itticket.common.api.BizException;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingRequestHeaderException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.util.List;

/**
 * 统一错误包络(PRD 21.1/21.3)。
 *
 * <p>错误响应不得包含内部提示词、堆栈、向量内容或未发布知识(AI-006),
 * 因此 5xx 只回固定文案,细节仅进服务端日志。
 */
@Slf4j
@Order(Ordered.HIGHEST_PRECEDENCE)
@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleApi(ApiException e) {
        return build(e.getCode(), e.getMessage(), e.getErrors(), e.getFallback());
    }

    /** common-web 的鉴权异常(缺少网关透传头)映射为 UNAUTHENTICATED。 */
    @ExceptionHandler(BizException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleLegacyAuth(BizException e) {
        ApiCode code = switch (e.getErrorCode()) {
            case NO_AUTH, USER_INVALID -> ApiCode.UNAUTHENTICATED;
            case FORBIDDEN -> ApiCode.FORBIDDEN;
            case PARAM_INVALID, ASSIGNEE_INVALID -> ApiCode.VALIDATION_ERROR;
            case IDEMPOTENT_CONFLICT -> ApiCode.IDEMPOTENCY_CONFLICT;
            case ILLEGAL_TRANSITION, NOT_CLAIMABLE, ALREADY_CLAIMED -> ApiCode.ILLEGAL_STATE_TRANSITION;
            case TICKET_NOT_FOUND -> ApiCode.OBJECT_NOT_FOUND;
            case SYSTEM_ERROR -> ApiCode.INTERNAL_ERROR;
        };
        return build(code, code.getDefaultMessage(), null, null);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleBodyValidation(MethodArgumentNotValidException e) {
        List<FieldIssue> issues = e.getBindingResult().getFieldErrors().stream()
                .map(fe -> new FieldIssue(fe.getField(), reasonOf(fe.getCode()), fe.getDefaultMessage()))
                .toList();
        return build(ApiCode.VALIDATION_ERROR, ApiCode.VALIDATION_ERROR.getDefaultMessage(), issues, null);
    }

    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleParamValidation(ConstraintViolationException e) {
        List<FieldIssue> issues = e.getConstraintViolations().stream()
                .map(v -> FieldIssue.invalid(lastNode(v), v.getMessage()))
                .toList();
        return build(ApiCode.VALIDATION_ERROR, ApiCode.VALIDATION_ERROR.getDefaultMessage(), issues, null);
    }

    @ExceptionHandler(MissingRequestHeaderException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleMissingHeader(MissingRequestHeaderException e) {
        return build(ApiCode.VALIDATION_ERROR, ApiCode.VALIDATION_ERROR.getDefaultMessage(),
                List.of(FieldIssue.required(e.getHeaderName(), "缺少必需请求头")), null);
    }

    /**
     * AI-004 与 OpenAPI 05 的 Schema 都是 additionalProperties=false。
     * 该约束由 application.yml 的 spring.jackson.deserialization.fail-on-unknown-properties=true 打开
     * (Spring Boot 默认是关闭的),未知字段在此落为 VALIDATION_ERROR。
     */
    @ExceptionHandler({HttpMessageNotReadableException.class, MethodArgumentTypeMismatchException.class})
    public ResponseEntity<ApiEnvelope<Void>> handleUnreadable(Exception e) {
        return build(ApiCode.VALIDATION_ERROR, ApiCode.VALIDATION_ERROR.getDefaultMessage(),
                List.of(FieldIssue.invalid("body", "请求体格式无效或包含未声明字段")), null);
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleNoResource(NoResourceFoundException e) {
        return build(ApiCode.OBJECT_NOT_FOUND, ApiCode.OBJECT_NOT_FOUND.getDefaultMessage(), null, null);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiEnvelope<Void>> handleUnknown(Exception e) {
        log.error("[consultation] 未捕获异常 requestId={}", RequestContext.get(), e);
        return build(ApiCode.INTERNAL_ERROR, ApiCode.INTERNAL_ERROR.getDefaultMessage(), null, null);
    }

    private static String reasonOf(String constraintCode) {
        return "NotNull".equals(constraintCode) || "NotBlank".equals(constraintCode) ? "REQUIRED" : "INVALID";
    }

    private static String lastNode(ConstraintViolation<?> violation) {
        String path = violation.getPropertyPath().toString();
        int dot = path.lastIndexOf('.');
        return dot < 0 ? path : path.substring(dot + 1);
    }

    private static ResponseEntity<ApiEnvelope<Void>> build(ApiCode code, String message,
                                                           List<FieldIssue> errors, String fallback) {
        return ResponseEntity.status(code.getHttpStatus())
                .body(ApiEnvelope.error(code, message, RequestContext.get(), errors, fallback));
    }
}
