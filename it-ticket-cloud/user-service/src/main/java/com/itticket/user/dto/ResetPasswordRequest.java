package com.itticket.user.dto;

import lombok.Data;

/** 主管重置他人密码 */
@Data
public class ResetPasswordRequest {
    private String newPassword;
}
