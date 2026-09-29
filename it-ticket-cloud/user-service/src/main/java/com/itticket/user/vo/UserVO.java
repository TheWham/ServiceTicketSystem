package com.itticket.user.vo;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

/** 对外输出的用户信息(snake_case,与旧版 SQLite 行字段一致) */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class UserVO {
    private String userId;
    private String name;
    private String role;
    private String department;
    /** 主管账号列表才返回：员工号/账号状态 */
    private String employeeNo;
    private String status;
    @com.fasterxml.jackson.annotation.JsonProperty("display_name")
    public String displayName() { return name; }
    public Boolean getEnabled() { return status == null ? true : "ACTIVE".equals(status); }

    /** 4 参：登录/派单选择等基础场景 */
    public UserVO(String userId, String name, String role, String department) {
        this.userId = userId;
        this.name = name;
        this.role = role;
        this.department = department;
    }

    /** 6 参：主管账号列表（含员工号/状态） */
    public UserVO(String userId, String name, String role, String department, String employeeNo, String status) {
        this(userId, name, role, department);
        this.employeeNo = employeeNo;
        this.status = status;
    }
}
