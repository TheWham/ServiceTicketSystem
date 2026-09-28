package com.itticket.user.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 角色授权（PRD-Ultimate §20：user_id, role_code, granted_by, granted_at, revoked_at） */
@Data
@TableName("user_role")
public class UserRoleEntity {
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;
    private String userId;
    /** EMPLOYEE / ENGINEER / HUMAN_CS / AI_CS / PLATFORM_ADMIN（§5.1） */
    private String roleCode;
    private String grantedBy;
    private LocalDateTime grantedAt;
    private LocalDateTime revokedAt;
}
