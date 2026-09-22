package com.itticket.common.web;

import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.api.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

/**
 * 全局异常处理 —— 对应旧版 errorHandler.js:
 * BizException 按 {code,msg,data} + 对应 HTTP 状态返回;未捕获异常兜底 500/50000。
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BizException.class)
    public ResponseEntity<Result<Void>> handleBiz(BizException e) {
        return ResponseEntity
                .status(HttpStatus.valueOf(e.getErrorCode().getHttpStatus()))
                .body(Result.err(e.getErrorCode().getCode(), e.getMessage()));
    }

    @ExceptionHandler({MethodArgumentNotValidException.class, HttpMessageNotReadableException.class,
            MethodArgumentTypeMismatchException.class})
    public ResponseEntity<Result<Void>> handleBadRequest(Exception e) {
        String msg = e instanceof HttpMessageNotReadableException ? "请求体格式无效" : e.getMessage();
        return ResponseEntity.status(400).body(Result.err(ErrorCode.PARAM_INVALID.getCode(), msg));
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<Result<Void>> handleNotFound(NoResourceFoundException e) {
        return ResponseEntity.status(404).body(Result.err(40400, "接口不存在: " + e.getResourcePath()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Result<Void>> handleUnknown(Exception e) {
        log.error("[ERROR] 未捕获异常: {}", e.getMessage(), e);
        return ResponseEntity.status(500)
                .body(Result.err(ErrorCode.SYSTEM_ERROR.getCode(),
                        e.getMessage() == null ? ErrorCode.SYSTEM_ERROR.getMsg() : e.getMessage()));
    }
}
