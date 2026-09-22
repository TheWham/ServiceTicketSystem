package com.itticket.common.api;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 统一响应包裹 {code, msg, data},code=0 成功 —— 与旧版格式一致。
 * data 为 null 时序列化省略该字段(旧版错误响应带 data:null,前端只读 code/msg,此差异无影响)。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Result<T> {
    private int code;
    private String msg;
    private T data;

    public static <T> Result<T> ok() {
        return new Result<>(0, "success", null);
    }

    public static <T> Result<T> ok(T data) {
        return new Result<>(0, "success", data);
    }

    public static <T> Result<T> ok(String msg, T data) {
        return new Result<>(0, msg, data);
    }

    public static <T> Result<T> err(ErrorCode errorCode) {
        return new Result<>(errorCode.getCode(), errorCode.getMsg(), null);
    }

    public static <T> Result<T> err(ErrorCode errorCode, String msg) {
        return new Result<>(errorCode.getCode(), msg, null);
    }

    public static <T> Result<T> err(int code, String msg) {
        return new Result<>(code, msg, null);
    }
}
