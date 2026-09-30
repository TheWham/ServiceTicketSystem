package com.itticket.consultation.service;

import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.consultation.api.ApiExceptionHandler;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * 会话不存在时的错误响应契约：
 * 对外必须统一为 HTTP 404 + 业务码 OBJECT_NOT_FOUND（历史 SESSION_NOT_FOUND 属内部编码），
 * 前端据此渲染“会话不存在”而非“服务器错误”。
 */
class SessionErrorContractTest {

    /** BizException(SESSION_NOT_FOUND) 经全局异常处理器后：状态码 404，body.code 必须是规范 OBJECT_NOT_FOUND */
    @Test
    void missingSessionUsesObjectNotFoundEnvelope() {
        var response = new ApiExceptionHandler().handleLegacyAuth(new BizException(ErrorCode.SESSION_NOT_FOUND));
        assertEquals(404, response.getStatusCode().value());
        assertEquals("OBJECT_NOT_FOUND", response.getBody().code());
    }
}