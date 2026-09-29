package com.itticket.user.dto;

import lombok.Data;

/** 修改密码（登录用户，需旧密码校验） */
@Data
@com.fasterxml.jackson.databind.annotation.JsonNaming(com.fasterxml.jackson.databind.PropertyNamingStrategies.SnakeCaseStrategy.class)
public class ChangePasswordRequest {
    @com.fasterxml.jackson.annotation.JsonAlias("oldPassword")
    private String oldPassword;
    @com.fasterxml.jackson.annotation.JsonAlias("newPassword")
    private String newPassword;
}
