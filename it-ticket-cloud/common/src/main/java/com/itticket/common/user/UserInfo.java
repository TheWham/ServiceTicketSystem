package com.itticket.common.user;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 用户信息（内部 HTTP 同样使用 PRD snake_case 字段）
 * user-service 的 /api/internal/users 接口返回此结构,gateway 与 ticket-service 消费
 */
@Data
@NoArgsConstructor
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class UserInfo {
    private String userId;
    private String name;
    private String role;
    @JsonAlias("department")
    private String departmentId;
    private String status;
    private String employeeNo;
    private String identitySource;

    public UserInfo(String userId, String name, String role, String departmentId, String status) {
        this.userId = userId;
        this.name = name;
        this.role = role;
        this.departmentId = departmentId;
        this.status = status;
    }

    @JsonIgnore
    public String getDepartment() { return departmentId; }
}
