package com.itticket.user.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.user.enums.UserRole;
import com.itticket.user.enums.UserStatus;
import lombok.Data;

import java.time.LocalDateTime;

/** 用户表(it_user.user) */
@Data
@TableName("user")
public class User {
    @TableId(value = "user_id", type = IdType.INPUT)
    private String userId;
    private String name;
    private UserRole role;
    private String department;
    private String phone;
    private String wechatId;
    /** BCrypt 哈希(登录用,除 internal 接口外不对外输出) */
    private String passwordHash;
    private UserStatus status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
