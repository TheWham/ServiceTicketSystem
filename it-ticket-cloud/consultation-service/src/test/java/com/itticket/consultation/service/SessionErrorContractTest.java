package com.itticket.consultation.service;

import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.consultation.api.ApiExceptionHandler;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class SessionErrorContractTest {
    @Test void missingSessionUsesObjectNotFoundEnvelope() {
        var response = new ApiExceptionHandler().handleLegacyAuth(new BizException(ErrorCode.SESSION_NOT_FOUND));
        assertEquals(404, response.getStatusCode().value());
        assertEquals("OBJECT_NOT_FOUND", response.getBody().code());
    }
}
