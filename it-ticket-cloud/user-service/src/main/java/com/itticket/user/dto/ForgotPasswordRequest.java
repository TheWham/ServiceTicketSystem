package com.itticket.user.dto;

import lombok.Data;

/** 忘记密码（免登录）：工号+姓名+员工号三要素验证身份后重置 */
@Data
@com.fasterxml.jackson.databind.annotation.JsonNaming(com.fasterxml.jackson.databind.PropertyNamingStrategies.SnakeCaseStrategy.class)
public class ForgotPasswordRequest {
    @com.fasterxml.jackson.annotation.JsonAlias("userId")
    private String userId;
    @com.fasterxml.jackson.annotation.JsonAlias("display_name")
    private String name;
    @com.fasterxml.jackson.annotation.JsonAlias("employeeNo")
    private String employeeNo;
    @com.fasterxml.jackson.annotation.JsonAlias("newPassword")
    private String newPassword;
}
