package com.itticket.user.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.TableField;
import lombok.Data;

import java.time.LocalDateTime;

/** 用户表（PRD-Ultimate §20：user_id, employee_no, name, department_id, status, identity_source） */
@Data
@TableName("user_account")
public class User {
    @TableId(value = "user_id", type = IdType.INPUT)
    private String userId;
    /** 工号 */
    private String employeeNo;
    @TableField("display_name")
    private String name;
    /** 部门 ID */
    private String departmentId;
    /** ACTIVE / DISABLED */
    private Boolean enabled;
    private LocalDateTime lastIdentitySyncAt;
    private Long version;
    public String getStatus() { return Boolean.TRUE.equals(enabled) ? "ACTIVE" : "DISABLED"; }
    public void setStatus(String status) { enabled = "ACTIVE".equals(status); }
    /** SSO / LOCAL */
    private String identitySource;
    /** BCrypt 哈希（登录过渡用，非 PRD 字段；F-01 企业 SSO 上线后移除） */
    private String passwordHash;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
