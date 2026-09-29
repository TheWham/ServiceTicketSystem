package com.itticket.user.dto;

import lombok.Data;

/** 主管新建账号（admin_only，员工无自助注册） */
@Data
public class CreateUserRequest {
    private String userId;
    private String employeeNo;
    @com.fasterxml.jackson.annotation.JsonAlias("display_name")
    private String name;
    private String departmentId;
    private String roleCode;
    private String password;
}
