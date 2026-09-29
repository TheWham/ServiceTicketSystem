package com.itticket.user.dto;

import lombok.Data;

/** 主管新建账号（admin_only，员工无自助注册） */
@Data
@com.fasterxml.jackson.databind.annotation.JsonNaming(com.fasterxml.jackson.databind.PropertyNamingStrategies.SnakeCaseStrategy.class)
public class CreateUserRequest {
    @com.fasterxml.jackson.annotation.JsonAlias("userId")
    private String userId;
    @com.fasterxml.jackson.annotation.JsonAlias("employeeNo")
    private String employeeNo;
    @com.fasterxml.jackson.annotation.JsonAlias("display_name")
    private String name;
    @com.fasterxml.jackson.annotation.JsonAlias("departmentId")
    private String departmentId;
    @com.fasterxml.jackson.annotation.JsonAlias("roleCode")
    private String roleCode;
    private String password;
}
