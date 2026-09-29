package com.itticket.user.dto;

import lombok.Data;

/** 修改密码（登录用户，需旧密码校验） */
@Data
public class ChangePasswordRequest {
    private String oldPassword;
    private String newPassword;
}
