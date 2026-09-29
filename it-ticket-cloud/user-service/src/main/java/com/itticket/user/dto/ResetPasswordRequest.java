package com.itticket.user.dto;

import lombok.Data;

/** 主管重置他人密码 */
@Data
@com.fasterxml.jackson.databind.annotation.JsonNaming(com.fasterxml.jackson.databind.PropertyNamingStrategies.SnakeCaseStrategy.class)
public class ResetPasswordRequest {
    @com.fasterxml.jackson.annotation.JsonAlias("newPassword")
    private String newPassword;
}
