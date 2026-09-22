package com.itticket.common.api;

import lombok.Getter;

/** 业务异常:携带错误码,由 common-web 的全局异常处理器转为 {code,msg,data} 响应 */
@Getter
public class BizException extends RuntimeException {

    private final ErrorCode errorCode;

    public BizException(ErrorCode errorCode) {
        super(errorCode.getMsg());
        this.errorCode = errorCode;
    }

    public BizException(ErrorCode errorCode, String msg) {
        super(msg);
        this.errorCode = errorCode;
    }
}
