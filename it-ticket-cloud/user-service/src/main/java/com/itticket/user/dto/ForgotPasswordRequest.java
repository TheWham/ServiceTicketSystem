package com.itticket.user.dto;

import lombok.Data;

/** 忘记密码（免登录）：工号+姓名+员工号三要素验证身份后重置 */
@Data
public class ForgotPasswordRequest {
    private String userId;
    private String name;
    private String employeeNo;
    private String newPassword;
}
